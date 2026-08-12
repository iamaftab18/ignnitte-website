# Ignnitte — NEURA-style redesign (Flask)

A redesign of **ignnitte.com** with the visual language of **neura-robotics.com**:
a dark, near-black monochrome theme, oversized Space Grotesk display headings,
hairline-bordered panels, the signature "box + arrow" call-to-action, a full-screen
hero video, and a three.js wireframe accent.

**The content is unchanged** — every program, mentor, lab item and event is taken
directly from the original site (`../src`). Only the styling changed.

## Stack
- **Python Flask** + Jinja templates
- **Tailwind CSS** (Play CDN, configured inline in `base.html`)
- **JavaScript** for the hero typewriter, scroll reveals, mobile nav and forms
- **three.js** (r128) for the rotating wireframe object on the home page
- **SQLite** (`ignnitte.db`) for contact submissions, student registrations and
  visitor analytics

## Run

```bash
cd flask_site
pip install -r requirements.txt
cp .env.example .env   # then edit SECRET_KEY / ADMIN_USERNAME / ADMIN_PASSWORD
python app.py
# open http://localhost:5000
```

The database is created automatically on first run.

## Public routes
| Path | Page |
|------|------|
| `/` | Home (hero video, skill tracks, mentors, journey, testimonials) |
| `/programs` | Program details, highlights, full curriculum |
| `/internship` | Internship domains & path |
| `/about` | About / vision / mission / lab location |
| `/events` | Workshops & camps |
| `/lab-tour` | Lab equipment gallery |
| `/contact` | Contact form → SQLite |
| `/register` | Free student registration (no fees, no login) → SQLite |

Registration collects name, email, contact, gender, college, department, year of
study, CGPA and program interest, plus explicit consent to be contacted by email
or WhatsApp with further updates. There is **no payment and no student login** —
this is purely a data-collection form; on success the visitor sees an inline
confirmation, they are not redirected anywhere.

### Public API
- `POST /api/contact` — save a contact enquiry
- `POST /api/register` — save a student registration
- `GET  /api/health` — health check

## Admin panel (secret, not linked from the public site)
| Path | Purpose |
|------|---------|
| `/admin/login` | Sign in (session-based) |
| `/admin/dashboard` | Visitor count, analytics, registrations & contact tables |
| `/admin/export/registrations.csv` | Download all registrations |
| `/admin/export/contacts.csv` | Download all contact submissions |
| `POST /admin/logout` | End the admin session |

Default credentials (override via `.env`): `ADMIN_USERNAME=ignnitte01`,
`ADMIN_PASSWORD=admin@ignnitte`.

Every public GET page view (excluding `/admin`, `/api`, `/static`, `/assets`) is
logged to a `site_visits` table with an anonymous per-browser cookie ID, powering
the "Total visits" / "Unique visitors" / "Visits today" / "last 14 days" stats on
the dashboard. No personal data is captured for visit tracking.

## Assets
Images, the hero video and the logo are served from the original project's
`../public/` folder via the `/assets/...` route, so nothing was duplicated.

## Deployment notes
- Set a strong, random `SECRET_KEY` and change the default admin password before
  going live — see `.env.example`.
- `ignnitte.db` is created next to `app.py`; back it up regularly once real
  registrations start coming in.
- Run behind a production WSGI server (e.g. `gunicorn app:app`) rather than the
  Flask dev server.
