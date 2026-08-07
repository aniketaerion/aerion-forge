# M5.6 Validation Model

Plan validation shall detect at minimum:

- invalid contracts;
- empty plans;
- duplicate step identifiers;
- invalid step ordering;
- unknown dependency references;
- dependency cycles;
- destructive steps without approval;
- capability mismatches;
- blocking policy findings.

Validation output consists of:

- plan ID;
- valid flag;
- validation findings;
- finding severity;
- finding code;
- message;
- optional step reference;
- blocking flag.

A plan marked valid may not contain blocking findings.