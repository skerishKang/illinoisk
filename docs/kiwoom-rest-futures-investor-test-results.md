# Kiwoom REST futures investor data test results

## Purpose

This document records the live Kiwoom REST API test results for futures foreign/institutional investor data candidates.

The result of this test is that the current Kiwoom REST API path used by this project does not provide usable KOSPI200 futures foreign/institutional net buying data.

Therefore `scripts/scan_golden_cross.py::fetch_futures_frgn_inst()` must keep returning:

```python
{"frgn_net": 0, "inst_net": 0, "source": "unavailable"}
```

until a confirmed futures-specific source is found.

## Test environment

| Item | Value |
|------|-------|
| API | Kiwoom REST API |
| Token | 24-hour token issued successfully |
| Test date | 2026-06-10 |
| Market state | Intraday |

## Tested candidates

### opt50004

| Endpoint | API ID | Result |
|----------|--------|--------|
| `/api/dostk/rkinfo` | `opt50004` | unsupported API ID for this URI |
| `/api/dostk/chart` | `opt50004` | unsupported API ID for this URI |

Conclusion: not usable through the tested REST endpoints.

### opt10039 / opt10040

| Endpoint | API ID | Result |
|----------|--------|--------|
| `/api/dostk/rkinfo` | `opt10039` | unsupported API ID for this URI |
| `/api/dostk/chart` | `opt10039` | unsupported API ID for this URI |

Conclusion: not usable through the tested REST endpoints.

### ka10008 foreign trading trend

| Target | Endpoint | Result |
|--------|----------|--------|
| Stock code `005930` | `/api/dostk/frgnistt` | normal response with `stk_frgnr` rows |
| KOSPI200 futures `106F200` | `/api/dostk/frgnistt` | empty `stk_frgnr` array |
| `106F200_NX` | `/api/dostk/frgnistt` | empty `stk_frgnr` array |
| KOSPI index `001` | `/api/dostk/frgnistt` | empty `stk_frgnr` array |

Stock response fields observed:

| Field | Meaning |
|-------|---------|
| `chg_qty` | foreign net buying quantity; negative means net selling |
| `trde_qty` | foreign trading quantity |
| `wght` | foreign ownership ratio |

Conclusion: usable for individual stocks only, not for KOSPI200 futures.

### ka10010 / ka90004 program trading

The current scanner uses program trading data separately for stock-market program flow.

Conclusion: this is not a substitute for KOSPI200 futures foreign/institutional investor flow.

## Final conclusion

The tested Kiwoom REST API endpoints do not provide usable KOSPI200 futures foreign/institutional net buying data.

Keep the futures investor monitor in unavailable mode:

```python
{"frgn_net": 0, "inst_net": 0, "source": "unavailable"}
```

## Next options

1. Ask Kiwoom developer support whether a REST futures investor endpoint exists.
2. Consider legacy OpenAPI+ COM/OCX only if REST support is confirmed unavailable and the data is critical.
3. Consider a separate licensed data source if live futures investor flow is required.
4. Do not map stock foreign flow, stock program trading, or empty futures responses to futures foreign/institutional flow.

## Related files

- `docs/kiwoom-futures-investor-tr-audit.md`
- `scripts/scan_golden_cross.py::fetch_futures_frgn_inst()`
