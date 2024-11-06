# ro-crate-multiple-entrypoints

This RO-Crate metadata structure shows how the specification of RO-Crate could be extended
to support multiple entry points in an RO-Crate.
An entry point in this context can be considered as a kind of "lense"
through which the content of the RO-Crate can be seen.
This allows for a more flexible organization of related data, i.e by having one subgroup of files in the crate
representing a machine-actionable workflows with additional data within the same crate.

## Key differences to the RO-Crate 1.2 Draft specification
- Multiple Entry Points: Instead of a single entry point (`./`), this RO-Crate includes an additional entry point (`./workflow-subdirectory`) conforming to
the Workflow RO-Crate profile.
- All entry points can be identified by their additional type `Entrypoint`.
- Additionally, the `ro-crate-metadata.json` entity lists all entry points in its `about` property. The main entry point (`./`)
is pointed to by `mainEntity`

# Example Use Case

This structure is particularly useful for projects requiring a modular approach, where the main data repository (./) can be accompanied by one or more specialized workflows or datasets
that need to link to each others files.

# o-crate-multiple-entrypoints-workflow-and-process

Also shows an example on how RO-Crates could be expanded for multiple entry points.
This shows how a workflow run can be decomposed into an entry point for the workflow RO-Crate (only the executable workflow),
and another entry point for the process run RO-Crate representing the execution of said workflow.
