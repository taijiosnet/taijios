# taijios.net deploy from CI

Open work. Today `make -C site deploy` uploads the tested `build/site` from
Omega with the local wrangler login (see `site/README.md`).

- Pages credentials: `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` exist
  only as GitHub secrets of `taijiosnet/taiji`. Neither Gitea
  (`taijios/taijios`, the `taijios` org) nor the GitHub mirror
  `taijiosnet/taijios` has them. A CI deploy needs them added to the repository
  that runs it.
- Build inputs: the root bundle packs ZX bundles from `dis/` (`rill.zx`,
  `desktop_panel.zx`, the `dis/lib/*.zx` modules and the applications listed
  as `lazy` in `site/root.list`). They are build outputs and not in git, so a
  runner cannot rebuild the site from a checkout alone. Either the runner
  builds them (Ziran, Kryon and Rill pins) or a verified `build/site` is
  published as a release asset the deploy job downloads.
- Runner tools: Emscripten 6.0.6 with the zlib port, `ziran`, `mk` and
  `limbo`, and for the test `chromium`, `firefox` and `tesseract`.
- The old workflow `.github/workflows/pages.yml` in `taijiosnet/taiji` is still
  active: a push to its `master` or a manual run would deploy the retired site
  again over taijios.net. Disabling that workflow, or removing its secrets
  once a new deploy path has them, stops it.
