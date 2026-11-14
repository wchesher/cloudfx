# Team hub contract (backend and frontend build against this)

lumin8r's website is the convergence point: everything the team does today is reachable from it.

## Pages
- `GET /` -> `static/home.html`: public front door. What lumin8r is, two doors: "Build your file" (`/app`) and "Team" (`/team`). Use limits and the privacy line. No data.
- `GET /app` -> `static/index.html` (the employee bench, unchanged). `GET /` no longer serves it.
- `GET /team` -> `static/team.html`: the team hub (works signed-out: shows the code prompt).
- `GET /paste` -> `static/paste.html` (team-gated like every /api/station/* route).

## Team gate
- Env `LUMIN8R_TEAM_CODE` (set on the box with `update-lumin8r --set-key LUMIN8R_TEAM_CODE`).
- `POST /api/team/login {code}` -> 200 `{ok:true}` and sets cookie `lumin8r_team=<HMAC of code with a per-process random key>; HttpOnly; SameSite=Strict; Path=/` (add `Secure` when the request came through https: header `X-Forwarded-Proto: https`). Wrong code -> 401 `{error}`; after 5 wrong codes from one IP in 10 minutes -> 429.
- `POST /api/team/logout` clears the cookie.
- `GET /api/team/me` -> `{signed_in: bool, mode: "local"|"code"}`.
- If `LUMIN8R_TEAM_CODE` is unset: when env `LUMIN8R_REQUIRE_TEAM_CODE=1` (the box's unit sets it) every team route answers 503 `{error:"team code not set on this box: update-lumin8r --set-key LUMIN8R_TEAM_CODE"}`; otherwise (a laptop) team routes are open and `me` says `mode:"local"`.
- Gated: `/paste`, `/api/station/*`, `/api/team/*` (except login, logout, me). Not signed in -> 401 `{error:"team sign-in required"}`.

## People (step 1: collect kits)
- `GET /api/team/people` -> `{people:[{code, has_build, has_test, build_problems:[...], pasted:{A:n, B:n}, total_runs:n}], variants:[...], questions:[{id,type}]}`.
- `POST /api/team/people {code, build, test}` (`build`/`test` are the organizer JSON objects; `test` optional at upload) -> validates with `answers.parse_answers`, refuses a build that contains any held-out test ID (S02 S04 S06 W02 W04) or a test that contains build IDs, refuses a `code` not matching `^[A-Za-z0-9_-]{2,32}$` or not equal to `build.person_id`; saves under `MEFILE_PEOPLE_DIR/<code>/`. -> `{saved:true, problems:[...]}`.
- `POST /api/team/people/delete {code}` -> removes that folder (whole). -> `{deleted:true}`.

## Run, judge, results (steps 2-4)
- Paste runs: the existing paste station (`/paste?model=A|B`).
- `POST /api/team/run {model:"A", use_api:true}` -> when `ANTHROPIC_API_KEY` is set, answers every missing LLM A run through the API (runner.ask), saving into `llm_a.json` like the paste station; streams nothing; returns `{answered:n, errors:[...]}`. 503 when no key.
- `POST /api/team/experiment {judge:bool}` -> runs `experiment.run_experiment` in manual mode (pasted A and B; judge only when `judge` and a judge model distinct from LLM A is configured) -> `{summary:[...], results_md:"<markdown text>"}`.
- `GET /api/team/results` -> last `{summary, results_md}` or `{summary:[], results_md:""}`.
- `POST /api/team/ratesheet` -> builds the blind rating sheet from all pasted responses (judge.agreement) and returns `{url:"/api/team/files/ratesheet.html"}`; `GET /api/team/files/<name>` serves files from `DATA/team/` (names `[A-Za-z0-9._-]+` only).
- `POST /api/team/agreement {ratings:[<ratings json objects>]}` -> runs agreement against the last evaluations -> `{agreement_md:"..."}`.

## Final (step 5: freeze-day, 4:30-5:30)
- `POST /api/team/final/inputs {build, questions}` -> saves to `DATA/final/`, runs the converter (full scope, evidence_first unless env `LUMIN8R_FINAL_VARIANT`), refuses if the gate fails -> `{markdown, gate, questions:[{id,type,prompt,word_limit}], runs:[{run_id:"TEAM-A-<qid>"|"TEAM-B-<qid>", model, question_id}]}`. Team prefix from env `LUMIN8R_TEAM_NAME` (default `TEAM`).
- `GET /api/team/final` -> current final state: `{markdown|null, questions, runs:[{run_id, model, question_id, answer}], evaluations_ready:bool}`.
- `POST /api/team/final/answer {run_id, text}` -> saves into `DATA/final/responses.json` (comparison format).
- `POST /api/team/final/judge {test, comparisons}` -> saves both, runs the judge over our 8 + the 12 comparison responses (blind), writes `DATA/team/evaluations.json` and `.md` -> `{evaluations_md, counts:{ok, judge_error}}`. 503 if no distinct judge model/key.
- `GET /api/team/final/bundle` -> a zip of me.md, responses.json, evaluations.json/.md, results.md (the submission set).

## Docs
- `GET /api/team/docs` -> `{docs:[{name, title}]}` from the repo's `docs/*.md` (allowlist: strategy, pitch, risk-and-acceptance, market-research, frameworks-and-wethos, judge, voice-intake).
- `GET /api/team/docs/<name>` -> `{name, markdown}`.
- Links (static in the page): the team plan `https://claude.ai/artifact/JKTtNziv7f3KCN8koWhP6d`, the repo `https://github.com/wchesher/cloudfx`.

## Judge self-check (Common Kit section 9: "Report at least one case where it fails")
- `POST /api/team/selfcheck` -> runs `judge.eval_corpus.run_judge_selfcheck` with the real judge (`AnthropicJudgeBackend`; the fictional DEMO01 corpus only) -> `{passed, total, probes:[{name, expectation, result, passed, detail}], selfcheck_md, judge_model_requested, judge_models_served, at}`. Writes `DATA/team/selfcheck.json` (with the raw evaluations) and `selfcheck.md`. 503 `{error}` with no `ANTHROPIC_API_KEY` or on `JudgeConfigError` (for example the judge model equals the LLM A model).
- `GET /api/team/selfcheck` -> the last run without the raw evaluations, or `{passed:0, total:0, probes:[], selfcheck_md:""}`.
- Team page: judge station, "Can the judge tell good from poor?". `selfcheck.md` goes into the submission bundle.

## Provenance of runs (Common Kit section 9: "Record the model versions and how you loaded the file")
- `POST /api/station/answer` and `POST /api/team/final/answer` accept optional `model_shown` (text, the model name the chat window displayed; whitespace collapsed, at most 120 characters; anything but text -> 400). Each saved record carries `model_shown` (when given), `loading` and `pasted_at`. Paste-station records also carry `source:"paste"`.
- `loading` for pasted runs: `"new chat, memory and custom instructions off; me.md as message 1, question as message 2"` (no-profile paste runs: `"...; question as the only message"`). Runs answered by `POST /api/team/run` carry `source:"api"`, `model_served` (from the API response) and an API loading string.
- Pages: the paste station has a required-once field "Model name shown in the chat window", stored per model in `localStorage` (`lumin8r.model_shown.A|B`) and sent with every save; the final station has the same field for LLM A and LLM B (same keys), and refuses to save an answer until it is filled.
- `GET /api/team/final` adds `model_shown: {A, B}` (the last name saved with a final answer, to prefill another browser).
- `GET /api/team/final/bundle` adds `provenance.json` (`{loading_protocol, final:{A,B}, team_runs:{A,B}, judge, warnings, generated_at}`; per model: `model_shown[]`, `runs`, `pasted_runs`, `api_runs`, `loading[]`, `model_served[]`), `selfcheck.md` when run, `writeup.md` when `docs/writeup.md` exists, and `README.md` (run instructions).

## Questioning claims (employee bench, `/app`)
- The claim card has "Question this claim": "What is wrong or missing?" and Save. Questioned chips show a marker; the share station lists them ("You questioned N claims"). Page state only: never sent to the server.
- The corrected-answers download's `review_notes` is now an object: `{twin_reactions:[...], claim_questions:[{claim_id, claim_text, evidence, note, at}]}` (it was the twin-reaction list).
