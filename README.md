<h2>Progress Update 5/26/2026</h2>

I made good progress and I was able to fix the severity of vulnerabilities raised by CodeQL.

First of all, I tested different types of CodeQL scanning queries.

CodeQL has the following queries:

<img width="741" height="567" alt="CodeQL scanning queries" src="https://github.com/user-attachments/assets/2a0ecb2d-f44f-4956-910a-88da4d572f27" />


I went with the first option from the table above. I am using CodeQL code-scanning queries (default standard queries). Those queries are highly recommended for their high-precision scanning results. Those queries are highly optimized for production environments. They use vetted security rules that provide an extremely low false-positive rate.

Running the PRs scans with those default CodeQL queries classified the vulnerabilities discovered to just warning. CodeQL uses a level attribute from the SARIF scanning result file. This level field value was mapping each vulnerability to a warning.

To correctly map the severity of the vulnerability, I had to hardcode the list of the CWE (Common Weakness Enumeration) TOP 25 in the vulnerability classification code. I extracted the mapped CWE number from the CodeQL scanning tags attribute (CWE IDs) array to check if it matches one of the hardcoded CWE TOP 25. The vulnerability severity will be escalated to high (critical) if it is found in the CWE TOP 25 list.

This is the list of CWE TOP 25 added:

CWE_TOP_25 = \[

'CWE-787', 'CWE-079', 'CWE-089', 'CWE-020', 'CWE-125', 'CWE-078', 'CWE-416',

'CWE-022', 'CWE-352', 'CWE-434', 'CWE-476', 'CWE-502', 'CWE-190', 'CWE-287',

'CWE-798', 'CWE-862', 'CWE-732', 'CWE-269', 'CWE-306', 'CWE-362', 'CWE-522',

'CWE-611', 'CWE-918', 'CWE-077', 'CWE-400', 'CWE-088', 'CWE-094'

\]

In the final summary scan report, I am also reporting the Top 5 CWE found when scanning the PRs.

<img width="1886" height="1061" alt="AI PRs Analysis Summary" src="https://github.com/user-attachments/assets/ae2259ad-5df8-4741-8e1c-df934e0c5785" />

