# Macro for Ancient Iranian Languages processing
# Usage: /macro.run ail_run persian_history_scripts "Persian Language History & Scripts/Texts"

# This macro would perform:
# /ingest.synth sources/${1|slug}_corpus.md books/${1|slug}.synth.md 100 16000
# /book.zero2hero ${2} --plan
# /exam.cram ${2}
