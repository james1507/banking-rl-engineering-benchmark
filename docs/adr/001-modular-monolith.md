# ADR-001: One posting transaction
Context: money, replay and event must agree under failures.
Decision: modular monolith with explicit application-owned SQL transaction.
Consequences: atomic local state; notifications use outbox after commit.
Rejected: microservices/sagas for internal transfers; extra failure states without product need.
Evidence: rollback/crash integration tests, linked from evidence index when executed.
