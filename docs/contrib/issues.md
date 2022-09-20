# Using the issue tracker

Reporting bugs and requesting new features is done one the [tsrc issue tracker on GitHub](https://github.com/your-tools/tsrc/issues).

## Reporting bugs

If you are reporting a bug, please provide the following information:

* `tsrc` version
* Details about your environment (operating system, Python version)
* The exact command you run
* The full output

Doing so will ensure we can investigate your bug right away.


## Suggesting new features

If you think `tsrc` is lacking a feature, please provide the following information:

* What exactly is your use case?
* Do you need a new command-line option or even a new command?
* Do you need changes in the configuration files?

Note that changing`tsrc` behavior can get tricky.

First off, we want to avoid *data loss* following a `tsrc` command above

Second, we want to keep `tsrc` behavior as least surprising as possible, so that
it can be used without having to read (too much of) documentation.

To that end, and keeping in mind `tsrc` needs to accommodate a large
variety of use cases, we want to keep the code:

* easy to read and,
* easy to maintain,
* and very well tested.

The best way to achieve all of this is to *keep it simple*.

This means we'll be very cautious before implementing a new feature, so
don't hesitate to open an issue for discussion before jumping into the
development of a new feature.


