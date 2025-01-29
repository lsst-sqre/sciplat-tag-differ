#!/usr/bin/env python3

import json

from pathlib import Path
from copy import deepcopy
import sys

def main() -> None:
    ghcr=Path("ghcr.io.contents.json")
    dockerhub=Path("docker.io.contents.json")

    ghcr_obj=json.loads(ghcr.read_text())
    dockerhub_obj=json.loads(dockerhub.read_text())

    ghcr_tags: dict[str, list[str]] = {}
    dockerhub_tags: dict[str, list[str]] = {}

    ghcr_shas: dict[str,str] = {}
    dockerhub_shas: dict[str,str] = {}

    for sha in ghcr_obj["data"]:
        ghcr_tags[sha]=[x for x in ghcr_obj["data"][sha]["tags"]]
        for tag in ghcr_tags[sha]:
            ghcr_shas[tag] = sha

    for sha in dockerhub_obj["data"]:
        dockerhub_tags[sha]=[ x for x in dockerhub_obj["data"][sha]["tags"]]
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

    exclude = check_for_conflicts(ghcr_shas, dockerhub_shas)
    print(f"Problematic tags: {exclude}")
    
    ghcr_needs: list[str] = tag_compare(ghcr_tags, dockerhub_tags, exclude)

    outfile=Path("ghcr-needs.json")
    outfile.write_text(json.dumps(ghcr_needs, sort_keys=True, indent=2))

    outfile=Path("transfer-tags.sh")
    out_text = "#!/bin/sh\n\n# Copy docker tags from Docker Hub to ghcr.io\n\n"
    t=1
    for tag in ghcr_needs:
        out_text += f"# {t}\n"
        out_text += f"docker pull docker.io/lsstsqre/sciplat-lab:{tag}\n"
        out_text += (f"docker tag docker.io/lsstsqre/sciplat-lab:{tag} "
                     f"ghcr.io/lsst-sqre/sciplat-lab:{tag}\n")
        out_text += f"docker push ghcr.io/lsst-sqre/sciplat-lab:{tag}\n"
        out_text += f"docker rmi -f docker.io/lsstsqre/sciplat-lab:{tag}\n"
        out_text += f"docker rmi -f ghcr.io/lsst-sqre/sciplat-lab:{tag}\n"
        out_text += "docker image prune -f\n"
        out_text += "docker builder prune -f\n\n"
        t+=1

    for tag in exclude:
        out_text += f"# {t}\n"
        out_text += f"docker pull docker.io/lsstsqre/sciplat-lab:{tag}\n"
        out_text += (f"docker tag docker.io/lsstsqre/sciplat-lab:{tag} "
                     f"ghcr.io/lsst-sqre/sciplat-lab:exp_{tag}_docker_io\n")
        out_text += f"docker push ghcr.io/lsst-sqre/sciplat-lab:exp_{tag}_docker_io\n"
        out_text += f"docker rmi -f docker.io/lsstsqre/sciplat-lab:{tag}\n"
        out_text += f"docker rmi -f ghcr.io/lsst-sqre/sciplat-lab:exp_{tag}_docker_io\n"
        out_text += "docker image prune -f\n"
        out_text += "docker builder prune -f\n\n"
        t +=1
        
    out_text += "# That's all, folks.\n"

    outfile.write_text(out_text)
    
        

def tag_compare(ghcr: dict[str, list[str]], docker: dict[str, list[str]],
                exclude: list[str]
                ) -> dict[str, list[str]]:
    """Find tags in docker.io not at ghcr.io"""
    retval: list[str] = []
    for sha in docker:
        print(f"considering {docker[sha]}: {sha}")
        # I think we're going to have to do a pull/push anyway...
        for tag in docker[sha]:
            print(f"tag: {tag}")
            if ( tag and
                 tag not in exclude and
                 not tag.startswith("exp_") and
                 not tag.startswith("latest_") and
                 not tag.startswith("recommended") ):
                if sha not in ghcr:
                    print(f"sha {sha} not at ghcr")
                    retval.append(tag)
                else:
                    if tag not in ghcr[sha]:
                        print(f"tag {tag} not in in ghcr tags for {sha}")
                        retval.append(tag)
                    else:
                        print(f"{tag} -> {sha} exists at both places")
            else:
                print(f"Skipping tag '{tag}'")

    return retval

def check_for_conflicts(ghcr: dict[str, str],
                        docker: dict[str, str]) -> list[str]:
    """See if the same tag has different shas anywhere.  Return a list of
    those tags, which will need special handling."""
    retval: list[str] = []
    for tag in docker:
        sha = docker[tag]
        if tag in ghcr and ghcr[tag] != docker[tag]:
            print(
                f"tag {tag} is {ghcr[tag]} at ghcr but {docker[tag]} at docker"
            )
            if tag not in retval:
                retval.append(tag)
    for tag in ghcr:
        sha = ghcr[tag]
        if tag in docker and ghcr[tag] != docker[tag]:
            print(
                f"tag {tag} is {ghcr[tag]} at ghcr but {docker[tag]} at docker"
            )
            if tag not in retval:
                retval.append(tag)
    return retval
    
if __name__ == "__main__":
    main()
    
