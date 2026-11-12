# Screenshot provenance

Eight actual browser screenshots, captured locally on 12 November 2026. `swagger.jpg` shows the running application. The other seven show static documentation reports generated from recorded test/evaluation evidence. Those reports are not product dashboard screens.

| Image | Captured content | Primary evidence |
|---|---|---|
| [swagger.jpg](swagger.jpg) | Live FastAPI Swagger at `http://127.0.0.1:8010/docs` | Running local API, schema 0002 |
| [test-summary.jpg](test-summary.jpg) | 62 passed cases, module counts, suite time | [JUnit](../../evidence/readme-tests.xml), [make ci](../../evidence/readme-verification.log), [report](../../evidence/reviewer/test-summary.html) |
| [money-cases.jpg](money-cases.jpg) | All 22 money/concurrency/integration cases | [JUnit](../../evidence/readme-tests.xml), [report](../../evidence/reviewer/money-cases.html) |
| [security-cases.jpg](security-cases.jpg) | All 19 API/operator security cases | [JUnit](../../evidence/readme-tests.xml), [report](../../evidence/reviewer/security-cases.html) |
| [worker-cases.jpg](worker-cases.jpg) | All 9 worker/pool recovery cases | [JUnit](../../evidence/readme-tests.xml), [report](../../evidence/reviewer/worker-cases.html) |
| [domain-cases.jpg](domain-cases.jpg) | All 12 domain/safety cases | [JUnit](../../evidence/readme-tests.xml), [report](../../evidence/reviewer/domain-cases.html) |
| [rl-results.jpg](rl-results.jpg) | Baseline/golden/control/alternate results | [56-row matrix](../../evidence/validation-matrix.json), [report](../../evidence/reviewer/rl-results.html) |
| [operations.jpg](operations.jpg) | 11 scenarios, restore and measured HTTP profile | [Scenario reports](../../evidence/scenarios/), [restore](../../evidence/backup-restore.json), [load](../../evidence/load/result.json), [report](../../evidence/reviewer/operations.html) |

Application verification was rerun for this documentation update: 62 passed, 0 failures/errors/skips; one recorded adapter deprecation warning. Benchmark/scenario/restore/load sources retain their own original timestamps and were not silently rerun for the screenshots. Parameterized pytest entries count separately; generated Hypothesis examples do not add to the 62-case count.

The [manifest](provenance.json) records each image's SHA-256, byte count, saved capture time and source. Screenshots contain synthetic data, test identifiers and public endpoint descriptions; no live authentication tokens or runtime passwords.

## Rebuild and capture again

From the repository root:

```sh
make ci > docs/evidence/readme-verification.log 2>&1
python3 scripts/build_readme_evidence.py --junit artifacts/tests.xml
python3 -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/docs/evidence/reviewer/test-summary.html`. Follow each report link and take a full-page browser screenshot. Save JPEGs under the filenames above; capture the running `/docs` separately. Update the manifest hashes/timestamps after replacing images. Stop the temporary documentation server with Ctrl-C. Application money logic is not changed by the report builder.
