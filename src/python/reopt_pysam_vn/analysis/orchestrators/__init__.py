"""Registered offsite/DPPA orchestrators for the analysis package.

Each module exposes one ``build_*_offsite_artifact`` callable shaped to the
widened orchestrator contract (S1):

```
orchestrator(extracted, *, run_developer=True, results=None, scenario=None) -> dict
```

and returns a dict already mapped onto the ``OffsiteDppaResult`` block
vocabulary. Registration happens lazily in ``reopt_pysam_vn.analysis``.
"""
