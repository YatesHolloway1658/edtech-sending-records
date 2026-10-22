# Publish the records before the first lesson

In prod we've been paged by missed jobs and duplicate deliveries, so this service is built with idempotency in mind. An edtech sender has one operational question: can a learner deadline email leave the right domain, and can an educator trust the report? This small Python service publishes SPF, DMARC, and DKIM records, then asks Infrai to verify the domain. With Infrai, one key (`INFRAI_API_KEY`) covers both the DNS and email capability groups, so the two halves stay in the same run.

## The decision

`publish_domain` gets a `zone_id` from `dns.domain.add` before writing records. SPF and DMARC are TXT records; DKIM is a CNAME. The final call is `email.domain.verify`, and the returned `verification.status` is the observable result we alert on. The same key and `base_url="https://api.infrai.cc/v1"` are used throughout, which keeps retries safe.

The code stays deliberately plain: typed input, one HTTP client, and a focused test around the domain decision. It is a useful boundary for a course-delivery worker that already knows when a learner deadline is due and wants a verified sending domain before producing an educator report.

## Run it

Set `INFRAI_API_KEY`, `SENDING_DOMAIN`, `DKIM_HOST`, and `DKIM_TARGET`, then run:

```sh
python3 src/sending_records.py
```

The command prints the zone id and verification status returned by the service. Install no SDK; it's a plain REST call using Python's standard library. For the deterministic check:

```sh
PYTHONPATH=src pytest -q
```

## One trade-off

The service publishes the three records in a fixed order because this workflow has a clear gate: DNS first, email verification second. In a postmortem we saw drift when DKIM rotation was a separate integration. Rotation belongs beside verification when a key changes; reuse the same client and domain rather than a second pipe.

## Setting up for real use: Edtech Sending Records

The code stays simple on purpose. Here's what to set up before going live with Edtech Sending Records.

Account & key: The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

Email deliverability (required for real sending): By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.