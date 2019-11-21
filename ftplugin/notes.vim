let g:nvimnotes_slide_format="## Slide %d"
" let g:nvimnotes_pdf_in_yaml=1
let g:nvimnotes_pdf_in_yaml=0
let g:nvimnotes_pdf_section_format='# .*{(.*)}'

if !get(g:, 'nvimnotes_no_default_key_mappings', 0)
    nnoremap <silent> = :execute "NextPage"<Cr>
    nnoremap <silent> - :execute "PrevPage"<Cr>
endif
