# Failure semantics
Before commit: any exception/process death rolls back claimed key, debit/credit, ledger, transfer and outbox. After commit: data remains complete; caller repeats same semantic body/key and obtains stored outcome. No notification HTTP call is in financial transaction.
READ COMMITTED row locks use UUID order. SQLSTATE 40001/40P01/55P03 retries entire transaction, at most three attempts with small jitter. Pool/connection/statement failures return bounded 503; no terminal business rejection on transient failure. Connection loss at commit is deliberately uncertain.
Business rejection after ownership resolution persists REJECTED transfer and original response with zero journal/event. Authorization, missing resource and pre-claim validation failure do not persist claim.
Uvicorn handles graceful SIGTERM; worker stops polling via Event, leaves any failed lease reclaimable after 30s. No async work owns uncommitted money after response.
Outbox delivery is at-least-once. Receiver commits receipt/effect before acknowledgement. Lost acknowledgement retries safely; lease token fences stale worker acknowledgements. Independent notification events tolerate order changes.
