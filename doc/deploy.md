# Publishing

One `docs/` tree serves the whole site: `index.html` is the landing page, `app.html` the display,
and the manual is built into `docs/manual/`.

## GitHub Pages — the official location

`.github/workflows/pages.yml` builds the manual and publishes `docs/` on every push to `main`:

→ <https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep-eventdisplay/>

!!! warning "Pages needs the repository to be public, or a paid plan"
    GitHub Pages is not available for a **private** repository on a **free** plan, and the
    `delphi-fullDST-edm4hep` organisation is on the free plan — enabling it returns
    *"Your current plan does not support GitHub Pages for this repository."*

    Either make this repository public, as
    [delphi-edm4hep](https://github.com/delphi-fullDST-edm4hep/delphi-edm4hep) already is, or move
    the organisation to a paid plan. The workflow passes `enablement: true`, so Pages switches
    itself on the first time it can.

## CERN web area — temporary

```bash
tar -cf - -C docs . | ssh -K lxplus \
  'tar -xf - -C /eos/user/s/sqian/www/delphi-edm4hep-eventdisplay'
```

→ <https://sqian.web.cern.ch/delphi-edm4hep-eventdisplay/>

`ssh` needs `-K` (or `GSSAPIDelegateCredentials yes`); without a forwarded credential there is no
AFS token and you cannot read your own home directory. A Kerberos ticket (`kinit`) is required —
the public-key path is refused.

!!! warning
    `tar` does not consult `.gitignore`, so a file that is ignored still deploys. That once hid
    `docs/logo.png` being untracked: fine on EOS, a 404 on GitHub Pages.

!!! note "Temporary"
    The EOS copy exists so the display was shareable before Pages was switched on. GitHub Pages is
    the official location; keep EOS in step or retire it once Pages is live.

## What is committed

| | |
|---|---|
| committed | figure JSON (~0.5 MB), schema sidecars, the wheel the app installs, `docs/logo.png` |
| not committed | standalone `.html` (plotly.js inlined, ~5 MB), `docs/manual/` (built), `*.root` |

## After changing anything

```bash
delphi-display ... --view both      # regenerate the event figures
delphi-pages                        # rebuild docs/events/index.json
docs/build.sh                       # rebuild the wheel the browser app installs
mkdocs build                        # rebuild the manual into docs/manual/
```

`.github/workflows/ci.yml` lints, and fails if the committed wheel is stale against the source or
if the site references a file that is not there.
