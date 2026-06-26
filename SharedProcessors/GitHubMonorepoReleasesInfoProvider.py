#!/usr/local/autopkg/python
#
# Copyright 2026 Kevin M. Cox
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for GitHubMonorepoReleasesInfoProvider class"""

import re

from autopkglib import ProcessorError
from autopkglib.GitHubReleasesInfoProvider import GitHubReleasesInfoProvider

__all__ = ["GitHubMonorepoReleasesInfoProvider"]


class GitHubMonorepoReleasesInfoProvider(GitHubReleasesInfoProvider):
    """Like GitHubReleasesInfoProvider, but adds a 'tag_regex' input for
    monorepos that publish several components from one repo using
    per-component tag prefixes (e.g. 'cli/v1.4.2' alongside 'server/v2.1.0').

    The stock processor selects the newest release whose assets match
    'asset_regex', and derives 'version' by naively stripping a leading 'v'
    from the tag. Prefixed tags break the version: 'cli/v1.4.2' does not start
    with 'v', so 'version' comes out as the whole prefixed tag.

    This subclass:
      * restricts release selection to releases whose 'tag_name' matches
        'tag_regex', so sibling components are skipped even if their assets
        would otherwise satisfy 'asset_regex'; and
      * if 'tag_regex' contains a capture group, uses the first group as the
        'version' output instead of the naive leading-'v' strip.

    Everything else - pagination, prerelease handling, sort_by_highest_tag_names,
    private-repo auth, and all output variables - is inherited unchanged from
    the parent processor.
    """

    description = __doc__

    input_variables = dict(GitHubReleasesInfoProvider.input_variables)
    input_variables["tag_regex"] = {
        "required": False,
        "description": (
            "If set, only releases whose 'tag_name' matches this regex "
            "(via re.search) are eligible for selection. Use it to target a "
            "single component in a monorepo, e.g. '^cli/'. "
            "If the regex contains a capture group, the first group is used "
            "as the 'version' output variable; e.g. '^cli/v?(.+)$' "
            "yields '1.4.2' from the tag 'cli/v1.4.2'. Without a "
            "capture group, version derivation falls back to the parent's "
            "naive leading-'v' strip."
        ),
    }

    output_variables = dict(GitHubReleasesInfoProvider.output_variables)

    def select_asset(self, releases, regex):
        """Filter candidate releases by 'tag_regex' (if set) before deferring
        to the parent's asset-selection logic. Filtering here rather than in
        main() means the parent's pagination loop keeps fetching pages until
        it finds a tag-matching release that also has a matching asset."""
        tag_regex = self.env.get("tag_regex")
        if tag_regex:
            try:
                releases = [
                    rel for rel in releases if re.search(tag_regex, rel["tag_name"])
                ]
            except re.error as err:
                raise ProcessorError(f"Invalid tag_regex: {err}")
        # The parent raises NoMatchingReleaseError when nothing here is
        # eligible, which its main() catches to advance to the next page.
        super().select_asset(releases, regex)

    def main(self):
        # The parent does all the work: pagination, selection (through our
        # overridden select_asset), URLs, release notes, and a first pass at
        # 'version'.
        super().main()

        # If tag_regex supplied a capture group, prefer it for the version.
        tag_regex = self.env.get("tag_regex")
        if tag_regex:
            match = re.search(tag_regex, self.selected_release["tag_name"])
            if match and match.groups() and match.group(1):
                self.env["version"] = match.group(1)
                self.output(
                    f"Derived version '{self.env['version']}' from tag "
                    f"'{self.selected_release['tag_name']}' via tag_regex"
                )


if __name__ == "__main__":
    PROCESSOR = GitHubMonorepoReleasesInfoProvider()
    PROCESSOR.execute_shell()
