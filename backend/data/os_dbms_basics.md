# Process vs Thread

A process has its own address space; threads within a process share memory and have their own stack and registers. Thread context switches are cheaper.

# Deadlock

Deadlock needs four conditions: mutual exclusion, hold and wait, no preemption, circular wait. Break any one to prevent it.

# ACID Properties

Atomicity, Consistency, Isolation, Durability guarantee reliable database transactions.

# Normalization

1NF: atomic values. 2NF: no partial dependency on a composite key. 3NF: no transitive dependency. BCNF: every determinant is a candidate key.

# TCP vs UDP

TCP is connection-oriented, reliable, ordered, with congestion control. UDP is connectionless and faster with no delivery guarantee.
