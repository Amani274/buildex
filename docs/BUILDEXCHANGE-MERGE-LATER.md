# Merge later without changing main now

The local project folder contains Git history on `feature/buildexchange-zm`. Local main remains at `6d7bb311dc01c5241b64887adda7077a34c66072`. Two commits separate the inherited uncommitted Yebbo source snapshot from the BuildExchange implementation. The original checkout under Downloads was only read.

The downloadable source ZIP excludes `.git`, databases, environments and private photos. A sibling `BuildExchange-ZM-branch.bundle` preserves both branch refs and the commits for transfer. To inspect it in another local checkout:

```powershell
git bundle verify C:\path\to\BuildExchange-ZM-branch.bundle
git fetch C:\path\to\BuildExchange-ZM-branch.bundle feature/buildexchange-zm:review/buildexchange-zm
git switch review/buildexchange-zm
```

Only after repository access is restored: fetch the actual remote, compare its current default branch, review the inherited Yebbo snapshot commit separately, resolve any overlap on the feature branch, rerun tests and push that branch using your authorized GitHub account. Open a **draft** PR using BUILDEXCHANGE-DRAFT-PR.md, updated with actual remote base and validation. Do not force-update main or assume the old local origin/main equals current GitHub main.

No remote PR link exists for this handoff because the connected account could not access moonxight/yebbo. A local bundle transfers history; it does not grant GitHub push rights.
