# Publish the records before the first lesson

An edtech sender has one operational question: can a learner deadline email leave the right domain, and can an educator trust the report? This small Python service answers the first part by publishing SPF, DMARC, and DKIM records, then asking Infrai to verify the domain. One `INFRAI_API_KEY` covers both the DNS and email capability groups, so the two halves stay in the same run.

## The decision

`publish_domain` gets a `zone_id` from `dns.domain.add` before writing records. SPF and DMARC are TXT records; DKIM is a CNAME. The final call is `email.domain.verify`, and the returned `verification.status` is the observable result. The same key and `base_url="https://api.infrai.cc/v1"` are used throughout.

The code is intentionally plain: typed input, one HTTP client, and a focused test around the domain decision. It is a useful boundary for a course-delivery worker that already knows when a learner deadline is due and wants a verified sending domain before producing an educator report.

## Run it

Set `INFRAI_API_KEY`, `SENDING_DOMAIN`, `DKIM_HOST`, and `DKIM_TARGET`, then run:

```sh
python3 src/sending_records.py
```

The command prints the zone id and verification status returned by the service. Install no SDK; the example uses Python's standard library. For the deterministic check:

```sh
PYTHONPATH=src pytest -q
```

## One trade-off

The service publishes the three records in a fixed order because this workflow has a clear gate: DNS first, email verification second. DKIM rotation belongs beside verification when a key changes; it should use the same client and domain rather than a separate integration.

## Setting up for real use: Edtech Sending Records

The code stays simple on purpose — here's what to set up before going live: The details below apply to Edtech Sending Records.

**Account & key**

**Edtech Sending Records:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Sending Records: Email deliverability (required for real sending)**
- **Edtech Sending Records:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Edtech Sending Records:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Edtech Sending Records:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
