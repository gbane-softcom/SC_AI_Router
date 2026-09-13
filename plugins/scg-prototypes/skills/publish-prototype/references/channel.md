# Prototype channel

Machine-readable values live in `channel.json` next to this file; this page
explains the channel and what to do when something fails.

## What exists

- URL: `https://prototypes.softwarecombined.com/<slug>/`, one path per prototype.
- Storage: private S3 bucket `example-prototype-storage` in the SCG Production
  account (`000000000000`), reachable only through CloudFront with Origin Access
  Control. Content is public but unlisted, sends `X-Robots-Tag: noindex, nofollow`
  and expires 30 days after publish.
- Foundation: `example-infrastructure`, module `web-edge/static-site-cloudfront-s3`,
  manifest `environments/software-combined/production/web-edge-prototype-channel.yaml`.
- Archive: `example/prototype-archive`, `prototypes/<slug>/site/` is exactly
  what is served, `prototypes/<slug>/source/` is the project that produced it,
  `prototypes.json` is the registry that `list` reads.
- Scanner: publishing refuses to run with `GITLEAKS_CONFIG` or
  `GITLEAKS_CONFIG_TOML` set and verifies the SHA-256 of the binary recorded in
  `~/.config/scg-agent-git-hooks/config.json`. A machine without that pin cannot
  publish: install the `scg-review` plugin and run its review-setup skill.
- Identity: Identity Center permission set `ExamplePrototypePublisher` for account
  `000000000000`, used through the AWS profile `scg-prototypes`. It can only write
  this bucket's `prototypes/` prefix and invalidate this one distribution.

## When the channel is not deployed yet

`channel.json` has an empty `distributionId`, so every publish fails with
"the prototype channel is not deployed yet". The foundation deploy is owner
gated: deploy the manifest above, then record the distribution id from
`aws cloudformation describe-stacks --stack-name example-prototype-channel`.

## Failures

- **SSO expired** (`aws sts get-caller-identity --profile scg-prototypes` fails):
  run `aws sso login --profile scg-prototypes` and retry once.
- **Wrong account**: the script refuses when the profile resolves to any account
  other than `000000000000`.
- **gitleaks finding**: the publish stops before any write. Remove the secret,
  rotate it, and rebuild; never re-run with the finding in place.
- **Root-absolute references**: rebuild with the slug as the base path
  (`npm run build -- --base=/<slug>/`) or convert references to relative ones.
  Attribute values, `srcset` entries, CSS `url(...)` and `@import` are checked;
  absolute paths constructed inside JavaScript strings are not detected, so keep
  runtime fetches relative.
- **Symbolic links**: refused, because a link can resolve to content outside the
  prototype. Replace links with real files before publishing.
- **Slug already published**: choose another slug, or pass `--update` to replace
  an existing one deliberately.
- **Verification failed**: the artifact is published and invalidated; re-check
  the URL in a minute, and if it still fails confirm the slug prefix exists with
  `aws s3 ls s3://example-prototype-storage/prototypes/<slug>/`.
- **Link expired**: the archive still has the source; republish with
  `python3 <skill-dir>/scripts/prototypes.py publish ~/Documents/Github/prototype-archive/prototypes/<slug>/site --slug <slug> --update`.

## Unpublishing

`unpublish <slug>` deletes the S3 prefix, invalidates it and removes the registry
entry. The archived source stays in git, so keep the slug if you may republish.
