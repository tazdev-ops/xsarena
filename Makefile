.PHONY: bridge book dry continue snap verify jobs
bridge: ; xsarena ops service start-bridge-v2
book:   ; xsarena run book "$(SUBJECT)" --length long --span book --dry-run
dry:    ; xsarena run book "$(SUBJECT)" --dry-run
continue: ; xsarena run continue "$(BOOK)" --length long --span book --wait false --follow
snap:   ; xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
verify: ; xsarena ops snapshot verify
jobs:   ; xsarena ops jobs ls
