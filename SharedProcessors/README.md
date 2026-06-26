# GitHubMonorepoReleasesInfoProvider

A drop-in subclass of AutoPkg's core [`GitHubReleasesInfoProvider`](https://github.com/autopkg/autopkg/wiki/Processor-GitHubReleasesInfoProvider) for **monorepos that publish multiple components from a single repository using per-component tag prefixes** — for example `cli/v1.4.2` alongside `server/v2.1.0`.

## The problem it solves

The core processor selects the newest release whose assets match `asset_regex`, then derives the version by naively stripping a leading `v` from the tag. In a monorepo that breaks in two ways:

1. **Wrong release.** The newest release is whichever component was published most recently, not the one you want. `asset_regex` only helps if that component happens to ship a uniquely-named asset.
2. **Garbage version.** A prefixed tag like `cli/v1.4.2` doesn't start with `v`, so the `version` output becomes the whole string `cli/v1.4.2` instead of `1.4.2`.

This processor adds a single `tag_regex` input that fixes both.

## Input variables

Everything from `GitHubReleasesInfoProvider` is inherited unchanged (`github_repo`, `asset_regex`, `include_prereleases`, `sort_by_highest_tag_names`, `GITHUB_TOKEN_PATH`, pagination, etc.), plus:

| Variable | Required | Description |
|----------|----------|-------------|
| `tag_regex` | No | Only releases whose `tag_name` matches this regex (via `re.search`) are eligible for selection. Use it to target one component in a monorepo, e.g. `^cli/`. If the regex contains a capture group, the **first group** is used as the `version` output; e.g. `^cli/v?(.+)$` yields `1.4.2` from the tag `cli/v1.4.2`. Without a capture group, version derivation falls back to the parent's naive leading-`v` strip. |

Release selection still walks releases newest-first (or by highest tag if `sort_by_highest_tag_names` is set), skipping any release whose tag doesn't match `tag_regex`, and paginates until it finds a matching release that also has a matching asset.

## Output variables

Identical to `GitHubReleasesInfoProvider`: `url`, `asset_url`, `version`, `release_notes`, `asset_created_at`. (`version` is the one improved by `tag_regex`.)

## Example

```yaml
Process:
  - Processor: com.github.kevinmcox.SharedProcessors/GitHubMonorepoReleasesInfoProvider
    Arguments:
      github_repo: "exampleorg/monorepo"
      tag_regex: '^cli/v?(.+)$'
      asset_regex: 'mytool_.*_darwin_arm64\.tar\.gz'

  - Processor: URLDownloader
    Arguments:
      filename: "mytool.tar.gz"

  - Processor: EndOfCheckPhase
```

`tag_regex` adapts to whatever scheme the repo uses — `^cli/`, `^cli-v`, `^components/cli@`, etc. The capture group simply needs to wrap the part you want as the version.

## Notes

- **Private repositories.** Downloading a private repo's asset must go through the API `asset_url` (not the `browser_download_url`), with an `Accept: application/octet-stream` header and a token. Point `URLDownloader` at `%asset_url%` and add `request_headers` for `Authorization` and `Accept`.
- **Pagination.** Monorepos can bury a component's releases hundreds of entries deep; the inherited pagination loop handles this, so an authenticated `GITHUB_TOKEN` is recommended to stay within rate limits.
