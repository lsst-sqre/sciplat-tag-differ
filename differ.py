#!/usr/bin/env python3

import json

from pathlib import Path
from copy import deepcopy
import sys

def main() -> None:
    ghcr=Path("ghcr.io.contents.json")
    dockerhub=Path("docker.io.contents.json")

    ghcr_obj=json.loads(ghcr.read_text())
    dockerhub_obj=json.loads(ghcr.read_text())

    ghcr_tags: dict[str, list[str]] = {}
    dockerhub_tags: dict[str, list[str]] = {}

    ghcr_shas: dict[str,str] = {}
    dockerhub_shas: dict[str,str] = {}

    for sha in ghcr_obj["data"]:
        ghcr_tags[sha]=deepcopy(ghcr_obj["data"][sha]["tags"])
        for tag in ghcr_tags[sha]:
            ghcr_shas[tag] = sha

    for sha in dockerhub_obj["data"]:
        dockerhub_tags[sha]=deepcopy(ghcr_obj["data"][sha]["tags"])
        for tag in dockerhub_tags[sha]:
            dockerhub_shas[tag] = sha

    of1 = Path("dockerhub-by-tag.json")
    of1.write_text(json.dumps(dockerhub_shas, sort_keys=True, indent=2))
    of2 = Path("dockerhub-by-sha.json")
    of2.write_text(json.dumps(dockerhub_tags, sort_keys=True, indent=2))
    of3 = Path("ghcr-by-tag.json")
    of3.write_text(json.dumps(ghcr_shas, sort_keys=True, indent=2))
    of4 = Path("ghcr-by-sha.json")
    of4.write_text(json.dumps(ghcr_tags, sort_keys=True, indent=2))
            
    ghcr_needs: dict[str, list[str]] = tag_compare(ghcr_tags, dockerhub_tags)

    outfile=Path("ghcr-needs.json")
    outfile.write_text(json.dumps(ghcr_needs, sort_keys=True, indent=2))

def tag_compare(ghcr: dict[str, list[str]], docker: dict[str, list[str]]
                ) -> dict[str, list[str]]:
    """Find tags in docker.io not at ghcr.io"""
    retval: dict[str, list[str]] = {}

    check_for_conflicts(ghcr, docker)
    
    for sha in docker:
        print(f"considering {docker[sha]}: {sha}")
        # I think we're going to have to do a pull/push anyway...
        need_tags: list[str] = []
        for tag in docker[sha]:
            print(f"tag: {tag}")
            if ( tag and
                 not tag.startswith("exp_") and
                 not tag.startswith("latest_") and
                 not tag.startswith("recommended") ):
                if sha not in ghcr:
                    print(f"sha {sha} not at ghcr")
                    need_tags.append(tag)
                else:
                    if tag not in ghcr[sha]:
                        print(f"tag {tag} not in in ghcr tags for {sha}")
                        need_tags.append(tag)
                    else:
                        print(f"{tag} -> {sha} exists at both places")
            else:
                print(f"Skipping junk tag '{tag}'")
        if need_tags:
            retval[sha] = need_tags
                    
    return retval

def check_for_conflicts(ghcr: dict[str, list[str]],
                        docker: dict[str, list[str]]) -> None:
    """See if the same tag has different shas anywhere.  For now,
    explode if that is the case."""
    inv_g: dict[str,str] = {}
    inv_d: dict[str,str] = {}
    for sha in ghcr:
        for tag in ghcr[sha]:
            inv_g[tag] = sha
    for sha in docker:
        for tag in docker[sha]:
            inv_d[tag] = sha
    for tag in inv_g:
        if tag not in inv_d:
            continue
        if inv_d[tag] == inv_g[tag]:
            continue
        raise RuntimeError(
            f"tag {tag} is {inv_g[tag]} at ghcr but {inv_d[tag]} at docker"
        )
    for tag in inv_d:
        if tag not in inv_g:
            continue
        if inv_d[tag] == inv_g[tag]:
            continue
        raise RuntimeError(
            f"tag {tag} is {inv_g[tag]} at ghcr but {inv_d[tag]} at docker"
        )
            
    
if __name__ == "__main__":
    main()
    
