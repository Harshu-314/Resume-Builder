# AI Resume Builder — Backend

A Flask backend for an AI-powered resume builder: create resumes, get AI writing help, check your ATS score, and download a free PDF.

## Stack
- Flask + Flask-SQLAlchemy (SQLite by default)
- Flask-JWT-Extended (auth) + Flask-Bcrypt (passwords)
- Flask-Limiter (rate limiting)
- AI: Gemini or OpenAI (switch with one `.env` setting)
- fpdf2 (PDF generation)

## Setup

```bash
cd resume_builder_flask
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env:
#   - set a real SECRET_KEY and JWT_SECRET_KEY
#   - set AI_PROVIDER=gemini or openai
#   - paste the matching API key (GEMINI_API_KEY or OPENAI_API_KEY)
#   - EMAIL_PROVIDER defaults to "console" (verification codes print to the
#     server log — nothing to configure). Set EMAIL_PROVIDER=smtp + the
#     SMTP_* vars to actually send them (see "Email verification" below).

python seed.py                          # optional: demo user + sample resume
python migrate_email_verification.py    # only needed if you have an existing DB from before this feature
python migrate_password_reset.py        # only needed if you have an existing DB from before this feature
python run.py                           # starts on http://localhost:5000
```

Health check: `GET http://localhost:5000/api/health`

Demo login (if you ran `seed.py`): `demo@resumebuilder.test` / `Password123` (pre-verified, skips the OTP step)

## Auth
Every route except `/api/auth/*`, `/api/health`, and `/api/templates` requires:
```
Authorization: Bearer <token>
```
Get a token from `POST /api/auth/register` or `POST /api/auth/login`.

## Email verification

**No session until verified.** `POST /register` does *not* return a token — it creates the
account, generates a 6-digit OTP, hashes it (bcrypt, same as passwords — never stored in
plaintext), emails it, and stops there. `POST /login` checks the password but also refuses to
issue a token if `email_verified` is still false (it auto-sends a fresh OTP if the pending one
expired, so the person always has a usable code). The *only* way to get a token for a
password-signup account is `POST /verify-email` with the correct code — that's what actually
creates the session. The OTP expires after `OTP_EXPIRY_MINUTES` (default 10) and locks after
`OTP_MAX_ATTEMPTS` (default 5) wrong guesses, at which point `/resend-verification` (rate-limited,
60s cooldown by default) is required. Google Sign-In accounts skip all of this — Google has
already verified that email, so they get a token immediately.

- **Dev/demo (default, `EMAIL_PROVIDER=console`):** no setup needed. The OTP is written to the
  Flask server log instead of actually being emailed — read it from the terminal running `run.py`.
- **Real email (`EMAIL_PROVIDER=smtp`):** set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
  `SMTP_PASSWORD`, `EMAIL_FROM_ADDRESS` in `.env`. Works with Gmail (with an
  [app password](https://myaccount.google.com/apppasswords)), Mailtrap, or the SMTP relay of
  SendGrid/Resend/Amazon SES — any standard SMTP server.

`/verify-email` and `/resend-verification` are intentionally public routes (no `Authorization`
header) since, by design, there's no token yet at this point — they identify the account by
`email` in the body instead. Safety nets: unknown emails get a generic error (no account
enumeration on `/verify-email`), and the per-account OTP attempt lockout still applies regardless
of auth.

| Method | Route | Body | Notes |
|---|---|---|---|
| POST | `/verify-email` | `{email, otp}` | public; on success, returns `{token, user}` — this *is* the login |
| POST | `/resend-verification` | `{email}` | public; re-sends a fresh OTP (rate-limited) |

## API Reference

### Auth — `/api/auth`
| Method | Route | Body | Notes |
|---|---|---|---|
| POST | `/register` | `{name, email, password}` | password ≥ 8 chars; **no token returned** — sends a verification OTP instead |
| POST | `/login` | `{email, password}` | 403 with `details.email_verification_required` if not yet verified |
| POST | `/google` | `{id_token}` | Google Sign-In; auto-verified, token issued immediately |
| POST | `/verify-email` | `{email, otp}` | confirm the emailed code — issues the token |
| POST | `/resend-verification` | `{email}` | request a new code |
| POST | `/forgot-password` | `{email}` | sends a password-reset OTP (separate from the signup OTP) |
| POST | `/reset-password` | `{email, otp, new_password}` | confirms the code and sets a new password — issues the token |
| GET | `/me` | — | current user profile, incl. `email_verified` |

### Resumes — `/api/resumes`
| Method | Route | Body | Notes |
|---|---|---|---|
| GET | `` | — | list your resumes |
| GET | `/:id` | — | full resume incl. content |
| POST | `` | `{title, template_id, content, target_job_title?, target_job_description?}` | create |
| PUT | `/:id` | any of the above fields | partial update |
| DELETE | `/:id` | — | |

`content` shape:
```json
{
  "personal": {"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "portfolio": ""},
  "summary": "",
  "experience": [{"role": "", "company": "", "duration": "", "bullets": ["", ""]}],
  "education": [{"degree": "", "institution": "", "duration": "", "details": ""}],
  "skills": ["", ""],
  "projects": [{"name": "", "description": "", "bullets": [""], "tech_stack": [""]}],
  "certifications": [""]
}
```

### AI — `/api/ai`
| Method | Route | Body | Notes |
|---|---|---|---|
| POST | `/generate-resume` | `{profile, target_job_title?, resume_id?}` | turns raw Q&A answers into polished `content` |
| POST | `/improve-bullets` | `{bullets: [""], role_context?}` | rewrites weak bullets |
| POST | `/advisor/:resume_id` | — | qualitative resume feedback |
| POST | `/cover-letter/:resume_id` | `{job_description}` | Premium only |

### ATS Checker — `/api/ats`
| Method | Route | Body | Notes |
|---|---|---|---|
| POST | `/check/:resume_id` | `{job_description?}` | returns score 0-100 + breakdown + suggestions; free plan capped at 3 checks, premium unlimited |

### PDF — `/api/pdf`
| Method | Route | Notes |
|---|---|---|
| GET | `/download/:resume_id` | streams a PDF, free for all plans |

### Templates & Billing
| Method | Route | Notes |
|---|---|---|
| GET | `/api/templates` | list all templates: `id`, `label`, `category` (`resume`\|`cv`), `layout`, `accent`, `font`, `title_style`, `header_align` |
| POST | `/api/billing/upgrade` | demo-only: flips `user.plan` to `premium` — replace with a real payment webhook |
| POST | `/api/billing/downgrade` | back to `free` |

## Templates

25 templates total, built from 5 structural layout engines (`single`, `compact`, `banner`,
`timeline`, `sidebar_left`/`sidebar_right`) in `app/services/pdf_service.py`, each parameterized
by accent color, font, section-title style, and header alignment. The live Studio preview
(`frontend/app.js` → `renderPaperCanvas`) mirrors the same layout/accent/font per template so
what you see on screen matches the downloaded PDF.

**15 Resume templates** (`category: "resume"`) — fixed sections: summary, experience, projects,
education, skills, certifications. Single-column layouts (`minimal`, `modern`, `classic`,
`compact-ats`, `executive-navy`, `bold-graphite`, `mono-tech`) stay ATS-parseable on purpose;
sidebar/banner/timeline layouts (`sidebar-slate`, `sidebar-emerald`, `sidebar-right-coral`,
`timeline-indigo`, `timeline-charcoal`, `banner-crimson`, `banner-teal`, `gradient-violet`) trade
a little of that for visual style, which is fine for a resume a human will read.

**10 CV templates** (`category: "cv"`) — everything a resume has, plus long-form academic
sections that only render when present in the content: `publications`, `research_experience`,
`teaching_experience`, `conferences`, `grants_fellowships`, `awards_honors`, `affiliations`,
`references`. IDs: `academic-classic`, `academic-modern`, `research-focus`, `medical-clinical`,
`europass-style`, `two-column-academic`, `minimalist-cv`, `grants-fellowship`,
`teaching-focused`, `full-academic-longform`. CVs are allowed to run longer than one page — no
length nudging is applied to them.

To add a template: add an entry to `AVAILABLE_TEMPLATES` in `app/services/pdf_service.py` (pick
an existing `layout`, or add a new layout engine + register it in `LAYOUT_ENGINES`). No other
backend change is needed — `/api/templates`, template-id validation, and PDF generation all read
from that one dict. The frontend dropdowns and preview pick it up automatically on next load
since they're populated from `/api/templates` rather than hardcoded.

## Design notes
- ATS scoring is rule-based, not an AI call — instant, deterministic, and free to run.
- Resume PDF templates default to single-column on purpose — multi-column layouts break real ATS
  parsers. CV templates prioritize a complete academic record over ATS-parseability, per how CVs
  are actually used (academic/research hiring committees, not resume-parsing bots).
- Swapping AI providers is a one-line `.env` change, no code edits needed.
- The free-plan ATS limit lives on the `User` model (`FREE_ATS_CHECK_LIMIT`) so it's easy to tune.
- For production, replace `db.create_all()` with proper Flask-Migrate/Alembic migrations, and run behind `gunicorn`.

## License
All rights reserved to Lukka Harshitha. This code may not be copied, distributed, or used without permission.
