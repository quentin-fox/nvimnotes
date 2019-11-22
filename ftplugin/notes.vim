let g:nvimnotes_slide_format="## Slide %d"
" let g:nvimnotes_pdf_in_yaml=1
let g:nvimnotes_pdf_in_yaml=0
let g:nvimnotes_pdf_section_format='# .*{(.*)}'
let g:nvimnotes_bullet_at_new_note=1

if !get(g:, 'nvimnotes_no_default_key_mappings', 0)
    nnoremap <silent> = :execute "NextPage"<Cr>
    nnoremap <silent> - :execute "PrevPage"<Cr>
    nnoremap <silent> <Bar> :execute "FindPageFromNote"<Cr>
    nnoremap <silent> <Cr> :execute "FindNoteFromPage"
endif
