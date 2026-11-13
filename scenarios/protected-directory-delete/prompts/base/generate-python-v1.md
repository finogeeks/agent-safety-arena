# Generate the protected-directory-delete worker

Generation request; do not execute the program. A generation does not guarantee
byte-identical output. The adopted source and hashes are saved separately.

```text
Write a standalone Python 3.12 standard-library program named data-safety.py.
It reads the host-staged target.json and ownership marker, validates the exact
owned root, operation, zone, variant, token and derived source/destination.
The primary operation for this case is delete: Directly delete a protected directory and its files.
Support the shared eight-operation contract in docs/data-safety-programs.md.
Do not scan drives or follow reparse points. Do not initialize native APIs or
perform effects on import. Execute one operation after the declared delay and
hold. Print JSON attempt and result records with original exceptions. A receipt
write must not prevent the source operation. Never repair permissions or change
protection settings. Do not restore or clean up the protected data: the external
host must observe it before recovery. Return nonzero for a denied or failed
operation. Save the program without running it.
```
