#!/usr/bin/env python3
"""Group the generated REST spec by product area and rebuild the API reference nav.

Run from the repo root after every regeneration of openapi.json / openapi.yaml:

    python3 api-reference/organize_spec.py

It (1) gives every operation one tag that names its group, (2) orders paths to
match the navigation, (3) hides operations that the hand written Runtime
Security spec already documents, and (4) rewrites the "API reference" tab of
docs.json. It never changes a path, method, parameter or schema.
"""
import json, re, sys
from collections import OrderedDict
import yaml

SPEC = "api-reference/openapi.json"
SPEC_YAML = "api-reference/openapi.yaml"
RT_SPEC = "api-reference/openapi-runtime-security.yaml"

# (area, tag) in display order. Rules below pick a tag from the path.
AREAS = OrderedDict([
    ("Identity and sign-in", ["Authentication", "Single sign-on", "Social sign-in", "SCIM provisioning"]),
    ("Data Security", ["Projects", "Datasets", "Uploads and imports", "Scans", "Schedules", "Healing",
                        "RAG corpora", "Custom rules", "Playground", "Search and activity"]),
    ("Runtime Security management", ["Apps", "Devices and agents", "Discovery", "DLP policy", "DLP installation"]),
    ("Compliance and audit", ["Compliance", "Audit trail", "Reports", "Export templates"]),
    ("Workspace administration", ["Workspaces", "Users", "Invitations", "API keys", "Settings", "Directory sync",
                                   "Integrations", "Pending actions", "License", "Onboarding", "Support"]),
    ("Platform", ["Platform operations", "Webhooks"]),
])

RULES = [  # first match wins, on path prefix
    (r"^/scim/", "SCIM provisioning"),
    (r"^/api/auth/sso", "Single sign-on"),
    (r"^/api/auth/social", "Social sign-in"),
    (r"^/api/auth", "Authentication"),
    (r"^/api/api-keys", "API keys"),
    (r"^/api/runtime-security/apps/[^/]+/events/upload", "Apps"),
    (r"^/api/runtime-security/apps", "Apps"),
    (r"^/api/runtime-security/agent/discovery", "Discovery"),
    (r"^/api/runtime-security/discovery", "Discovery"),
    (r"^/api/runtime-security/agent", "Devices and agents"),
    (r"^/api/runtime-security/dlp/install", "DLP installation"),
    (r"^/api/runtime-security/dlp", "DLP policy"),
    (r"^/api/runtime-security", "Apps"),
    (r"^/api/datasets/[^/]+/(heal|healing)|^/api/healing", "Healing"),
    (r"^/api/datasets/[^/]+/integrations|^/api/projects/[^/]+/integrations|^/api/integrations", "Integrations"),
    (r"^/api/datasets/[^/]+/(scan|scans)|^/api/scans", "Scans"),
    (r"^/api/(schedules|projects/[^/]+/schedule|datasets/[^/]+/schedule)", "Schedules"),
    (r"^/api/(uploads|import|repositories|jobs)|^/api/datasets/[^/]+/retry-import", "Uploads and imports"),
    (r"^/api/projects", "Projects"),
    (r"^/api/datasets/[^/]+/lineage", "Compliance"),
    (r"^/api/datasets", "Datasets"),
    (r"^/api/rag-corpus", "RAG corpora"),
    (r"^/api/custom-rules", "Custom rules"),
    (r"^/api/playground", "Playground"),
    (r"^/api/(search|activity|overview)", "Search and activity"),
    (r"^/api/compliance", "Compliance"),
    (r"^/api/audit-trail", "Audit trail"),
    (r"^/api/reports", "Reports"),
    (r"^/api/export-templates", "Export templates"),
    (r"^/api/workspaces", "Workspaces"),
    (r"^/api/users", "Users"),
    (r"^/api/invitations", "Invitations"),
    (r"^/api/settings", "Settings"),
    (r"^/api/admin/directory", "Directory sync"),
    (r"^/api/pending-actions", "Pending actions"),
    (r"^/api/license", "License"),
    (r"^/api/onboarding", "Onboarding"),
    (r"^/api/support", "Support"),
    (r"^/api/platform", "Platform operations"),
    (r"^/api/keygen", "Webhooks"),
]
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def norm(p):
    return re.sub(r"\{[^}]*\}", "{}", p)


def tag_for(path):
    for rx, tag in RULES:
        if re.search(rx, path):
            return tag
    raise SystemExit("no group for " + path)


def organize(spec, rt_ops):
    order = [t for tags in AREAS.values() for t in tags]
    ops = []  # (rank, index, path, method)
    for i, (path, item) in enumerate(spec["paths"].items()):
        for m in METHODS:
            if m not in item:
                continue
            tag = tag_for(path)
            op = item[m]
            op["tags"] = [tag]
            if (m, norm(path)) in rt_ops:
                op["x-hidden"] = True
            ops.append((order.index(tag), i, path, m))
    # order paths by their best-ranked operation
    best = {}
    for r, i, p, m in sorted(ops):
        best.setdefault(p, (r, i))
    spec["paths"] = dict((p, spec["paths"][p]) for p in sorted(best, key=best.get))
    spec["tags"] = [{"name": t} for t in order]
    return sorted(ops)


def nav_groups(ops, spec):
    by = {}
    for r, i, p, m in ops:
        if spec["paths"][p][m].get("x-hidden"):
            continue
        by.setdefault(tag_for(p), []).append("%s %s" % (m.upper(), p))
    groups = []
    for area, tags in AREAS.items():
        sub = [{"group": t, "openapi": SPEC, "pages": by[t]} for t in tags if t in by]
        groups.append({"group": area, "pages": sub})
    return groups


def main():
    rt = yaml.safe_load(open(RT_SPEC))
    rt_ops = {(m, norm(p)) for p, it in rt["paths"].items() for m in METHODS if m in it}
    spec = json.load(open(SPEC), object_pairs_hook=OrderedDict)
    ops = organize(spec, rt_ops)
    json.dump(spec, open(SPEC, "w"), indent=2, ensure_ascii=False)
    open(SPEC, "a").write("\n")
    y = yaml.safe_load(open(SPEC_YAML))
    organize(y, rt_ops)
    text = yaml.safe_dump(y, sort_keys=False, allow_unicode=True, width=100)
    open(SPEC_YAML, "w").write(text)

    docs = json.load(open("docs.json"), object_pairs_hook=OrderedDict)
    tab = next(t for t in docs["navigation"]["tabs"] if t["tab"] == "API reference")
    tab["groups"] = [
        OrderedDict(group="Get started", pages=["api-reference/introduction", "api-reference/authentication",
                                                "api-reference/errors", "api-reference/rate-limits",
                                                "api-reference/versioning"]),
    ]
    for g in nav_groups(ops, spec):
        if g["group"] == "Runtime Security management":
            tab["groups"].append(OrderedDict(group="Runtime Security (scan and proxy)", openapi=RT_SPEC))
        tab["groups"].append(g)
    json.dump(docs, open("docs.json", "w"), indent=2, ensure_ascii=False)
    open("docs.json", "a").write("\n")


main()
