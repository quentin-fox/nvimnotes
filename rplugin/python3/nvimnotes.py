import pynvim
import subprocess
import uuid
import time
import re
from pathlib import Path


@pynvim.plugin
class NvimNotes(object):

    def __init__(self, nvim):
        self.nvim = nvim

    def get_settings(self):
        """Initializes settings from init.vim, called during :Annotate"""
        self._slide_section_str = self.nvim.eval('g:nvimnotes_slide_format')
        self._pdf_in_yaml = 1 == int(self.nvim.eval('g:nvimnotes_pdf_in_yaml'))
        if not self._pdf_in_yaml:
            self._pdf_section_str = self.nvim.eval('g:nvimnotes_pdf_section_format')

    def get_line(self, pattern: str, flags: str) -> int:
        # uses vim-style regex to search
        row, col = self.nvim.funcs.searchpos(pattern, flags)
        return (row - 1)

    def write_err(self, err: str):
        self.nvim.err_write(err + '\n')

    def write_msg(self, msg: str):
        self.nvim.msg_write(msg + '\n')

    def get_matching_lines(self, pattern: str, ln_range=None) -> tuple:
        buffer = self.nvim.current.buffer
        pat = re.compile(pattern)
        if not ln_range:
            matching = [(i, txt) for i, txt in enumerate(buffer) if pat.match(txt)]
        else:
            matching = [(i, txt) for i, txt in enumerate(buffer) if pat.match(txt) and i in ln_range]
        return matching

    def get_pdf_range(self):
        pdf_rng = self.get_match_ranges(pattern=self._pdf_section_str, unique=self.filename)
        return pdf_rng

    def get_slide_pos_in_notes(self, slide: int) -> int:
        pdf_rng = self.get_pdf_range()
        slide_pattern = self._slide_section_str.replace('%d', r'\d*')
        slide_unique = self._slide_section_str % slide
        slide_rng = self._get_match_ranges(slide_pattern, slide_unique, pdf_rng)
        return max(slide_rng)


    def get_match_ranges(self, pattern: str, unique: str, ln_range=None) -> range:
        """Divides the buffer up into sections separated by lines that match a specific regex, then returns the range (of lines) that corresponds to the section whose separator contains a unique strin
        Args:
            pattern: the regex used to split up the buffer into sections
            unique: the string that uniquely identifies one of the separators
            ln_range: the range of lines that will be split up into sections"""
        buflen = len(self.nvim.current.buffer)
        match_lines = self.get_matching_lines(pattern, ln_range=ln_range)

        # will be a list of tuples, tuples have the range for each pdf in the .notes file
        range_lines = []
        for i, tup in enumerate(match_lines):
            startln, txt = tup
            stopln = match_lines[i + 1][0] if i < (len(match_lines) - 1) else buflen
            newtup = (range(startln, stopln), txt)
            range_lines.append(newtup)

        pdf_range = next(rng for rng, pdfline in range_lines if unique in pdfline)
        return pdf_range

    @pynvim.command('Annotate', nargs='?')
    def annotate(self, args):
        self.get_settings()
        self.filename = args[0] if len(args) > 0 else self.get_filename()
        try:
            self.interface = Interface(self.filename)
        except (FileNotFoundError, OSError) as err:
            self.write_err(str(err))
        else:
            self.interface.open()

    def get_filename(self) -> str:
        buffer = self.nvim.current.buffer
        if self._pdf_in_yaml:
            pattern = r'^pdf: "?(.*pdf)"?$'
            pattern_vim = self.vimify_regex(pattern)
            yaml_pat = re.compile(pattern)

            file_ln = self.get_line(pattern_vim, 'bnc')
            file = buffer[file_ln]

            filename = yaml_pat.search(file).group(1)

        elif self._pdf_section_str:
            pattern_vim = self.vimify_regex(self._pdf_section_str)
            file_ln = self.get_line(pattern_vim, 'bnc')
            file = buffer[file_ln]
            section_pat = re.compile(self._pdf_section_str)
            filename = section_pat.search(file).group(1)
        return filename

    def vimify_regex(self, pattern: str) -> str:
        """Non-exhaustive function to convert python regex to vim regex"""
        newpat = pattern.replace('?', r'\=').replace('(', r'\(').replace(')', r'\)')
        return newpat

    @pynvim.command('GoPage', nargs=1)
    def go_page(self, args):
        new_page = args[0]  # defers type handling to interface
        try:
            self.interface.current_page = new_page
        except TypeError as err:
            self.write_err(str(err))
        except IndexError as err:
            self.write_err(str(err))

    @pynvim.command('CreatePageNote')
    def create_page_note(self):
        current_page = self.interface.current_page
        self.nvim.current.line = self._slide_section_str % current_page

    @pynvim.command('NextPage')
    def next_page(self):
        self.interface.next_page()

    @pynvim.command('PrevPage')
    def prev_page(self):
        self.interface.prev_page()

    @pynvim.command('CurrentPage')
    def current_page(self):
        cp = self.interface.current_page
        self.write_err(str(cp))


class Interface:

    def __init__(self, filename: str):
        f = Path(filename)
        if not f.exists():
            raise FileNotFoundError(f'{filename} could not be found in the working directory')
        elif f.suffix != '.pdf':
            raise OSError(f'{filename} is not a pdf file.')
        else:
            self.file = f
        self.server_code = str(uuid.uuid4()).replace('-', '')
        self._page_range = self._get_page_range()

    def _get_page_range(self):
        # uses pdfinfo since it's packaged with xpdf, no additional dependency
        pdf_info = subprocess.Popen(('pdfinfo', str(self.file)), stdout=subprocess.PIPE)
        pdf_info_stdout = pdf_info.communicate()[0]
        pdf_info_lst = pdf_info_stdout.decode('utf8').split('\n')
        pages = next((info for info in pdf_info_lst if "Pages" in info))
        page_int = int(re.sub(r'.*:\D*', '', pages)) # matches any non-digits
        return range(1, page_int + 1)

    def _send_command(self, command: str):
        args = (
            'xpdf',
            '-remote',
            str(self.server_code),
            command,
        )
        process = subprocess.Popen(args, stderr=subprocess.DEVNULL)
        return process

    def open(self):
        filename = str(self.file)
        start_cmds = [
            f'openFile({filename})',
            'singlePageMode',
            'closeSidebar',
            'zoomFitWidth'
        ]

        for i, cmd in enumerate(start_cmds):
            self._send_command(cmd)
            if i == 0:
                time.sleep(1.5)
            else:
                time.sleep(0.25)
        self._current_page = 1

    @property
    def current_page(self):
        return self._current_page

    @current_page.setter
    def current_page(self, page):
        try:
            page = int(page)
        except ValueError:
            raise TypeError(f'Page number must be an integer')
        else:
            if page not in self._page_range:
                raise IndexError(f'Page number must be between 1 and {max(self._page_range)}')
            else:
                self._send_command(f'gotoPage({page})')
                self._current_page = page

    def next_page(self):
        self._send_command('nextPage')
        if (self._current_page + 1) in self._page_range:
            self._current_page += 1

    def prev_page(self):
        self._send_command('prevPage')
        if (self._current_page - 1) in self._page_range:
            self._current_page += 1

    def quit(self):
        self._send_command('quit')


if __name__ == '__main__':
    from pynvim import attach
    nvim = attach('socket', path='/tmp/nvim')
    nn = NvimNotes(nvim)
    nn.annotate(args=[])


