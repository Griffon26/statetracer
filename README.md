# statetracer
Statetracer is a python program state tracer that can easily be integrated 
into an existing program to trace all changes to a selected subset of the
program state.

First you define per class which member variables you're interested in by
applying the `@statetracer` decorator to the class. Then when you enable
tracing for an instance of that class, all changes to the specified member
variables of the class will be traced. Members that hold basic types or
instances of non-decorated classes will be traced as strings, but if a
member variable is an instance of a decorated class, then only the selected
members of that class will be traced and so on.
