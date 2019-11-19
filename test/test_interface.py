import sys
import pytest
import time

sys.path.append('rplugin/python3/')

from nvimnotes import Interface


class TestInterface:

    @pytest.fixture(scope='class')
    def open_xpdf(self):
        i = Interface('test.pdf')
        i.open()
        yield i
        i.quit()

    def test_open_pdf(self, open_xpdf):
        i = open_xpdf
        assert i.current_page == 1

    def test_open_missing_pdf(self):
        with pytest.raises(FileNotFoundError):
            Interface('test_missing.pdf')

    def test_non_pdf(self):
        with pytest.raises(OSError, match=".* is not a pdf file."):
            Interface('test.txt')

    def test_change_page(self, open_xpdf):
        i = open_xpdf
        i.current_page = 5
        assert i.current_page == 5

    def test_change_invalid_page(self, open_xpdf):
        i = open_xpdf
        with pytest.raises(TypeError, match=".* must be an integer"):
            i.current_page = "test"
        with pytest.raises(IndexError, match="Page number must be between 1 and .*"):
            i.current_page = -1
        with pytest.raises(IndexError, match="Page number must be between 1 and .*"):
            i.current_page = 22

