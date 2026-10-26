# Pakistan AI — free automation starter

Built for Muhammad Ali Baqar, 25 October 2026.

## What is ready

A Docker Compose deployment with n8n, a Python/SQLite editorial worker and Ollama; two importable n8n workflows; optional Gemini API support; an editorial queue; a 30-day campaign limit; explicit publication receipts; and automated tests.

**Status: locally built and unit-tested, not deployed.** No Oracle account, AI key or LinkedIn OAuth connection has been configured. Docker and n8n runtime/import testing were unavailable in the build environment. Treat the workflows as an integration starter until you complete the live checks below.

No paid API or paid hosting is configured. Gemini is off by default. No browser cookies, passwords, CV or other private account data are included.

## Actual scope of version 0.1

- Collect AI-related RSS stories twice daily, reject missing/old/future dates, deduplicate by canonical URL, and generate up to two drafts per research run.
- Use a local model by default, or an explicitly configured Gemini free-tier API project.
- Keep drafts in review until someone checks the source and approves them. RSS snippets and a language model do NOT independently verify news.
- Publish only approved fresh posts in noon/7 PM PKT test slots, maximum two per PKT calendar day and at least six hours apart.
- Stop research and new publication claims 30 days after the database is first initialized. The server itself remains running until stopped. Change `campaign_days` in config if desired.
- Block further publishing if a previous attempt has an unknown result, preventing automatic duplicate retries. Record a LinkedIn post URN before marking a post published.
- Export content and manually recorded analytics.

Not included: live X or Instagram collection, Google Trends measurements, video transcription, automatic hashtags analysis, cross-source fact verification, adaptive engagement optimization, automatic like/comment bots, or LinkedIn personal analytics API access. Creator names in config are an editorial reference list, not a functioning monitoring integration. No promise of virality or account growth is made.

A single relevant hashtag is added deterministically; it is not claimed to be trending. Drafts are news explanations, not reports of personal experiments. Videos can be added later as original publisher links; this version does not download or reupload footage.

## Hosting choice

Use an Oracle **Always Free eligible** Ubuntu Ampere A1 instance if capacity exists in your home region. Oracle documentation checked on 25 October lists a total allowance equivalent to 2 OCPUs/12 GB RAM and 200 GB combined boot/block storage; your console is authoritative. Suggested pilot: 2 OCPUs, 12 GB RAM, 50 GB boot volume. Never select paid resources or upgrade billing just to follow this guide.

Oracle can reclaim idle instances. Keep a private off-server backup. Running a twice-daily workflow does not guarantee exemption from reclamation; do not generate artificial CPU/network load to evade it. A free VM is not a guaranteed uptime service.

Use Docker Engine and the Docker Compose plugin from Docker's official Ubuntu installation instructions. Ports: allow SSH only from your address. By default n8n binds to loopback; worker and Ollama have no public ports. There is no need to expose 5678, 8787 or 11434 to the internet.

## Start on the VPS

Transfer/extract this folder to the VPS. Install Docker using the official instructions, then:

```sh
sh scripts/init.sh
docker compose pull
docker compose build
docker compose up -d
# One-time multi-GB download. Check disk space and free network allowance first.
docker compose exec ollama ollama pull qwen2.5:3b
docker compose ps
```

The model is a conservative small-model starting choice, not a benchmarked recommendation for your particular Oracle VM. Expect slow CPU generation; model availability, output quality, ARM compatibility and memory must be tested. Model failure stops drafting and records an error; it does not switch to a paid service. The worker limits queue growth to six waiting posts.

Compose uses upstream stable/latest image tags for initial setup. After the first successful test, record `docker compose images` and pin known-working image digests in `.env` with `N8N_IMAGE` and `OLLAMA_IMAGE`. Updates should be deliberate and backed up.

From your own computer, create a private SSH tunnel (replace the host):

```sh
ssh -L 5678:127.0.0.1:5678 ubuntu@YOUR_ORACLE_PUBLIC_IP
```

Open `http://localhost:5678` and create your n8n owner login. The development configuration disables secure cookies ONLY because the editor is localhost over an SSH tunnel. Never expose this HTTP configuration publicly.

### Public HTTPS, if needed for OAuth

If LinkedIn rejects a localhost OAuth callback, use a hostname you control (an eligible free DNS hostname can work), point it to the VPS, and enable the included HTTPS override. Set `PUBLIC_HOST` to the bare hostname in `.env`, then open OCI and OS firewall TCP 80/443. Use:

```sh
docker compose -f compose.yaml -f compose.https.yaml up -d
```

Caddy obtains HTTPS automatically when DNS and reachability are correct. This is not tested until a real hostname is connected. The override enables secure cookies. The worker/model remain private. Keep n8n owner authentication enabled. Do not send passwords, API keys, SSH private keys or tokens in chat.

## Connect the worker to n8n

1. Import `workflows/01_research.json` and `workflows/02_publish.json` from the n8n editor. Both are inactive initially.
2. Create a **Header Auth** credential named `Editorial worker`:
   - Name: `Authorization`
   - Value: `Bearer ` followed by `WORKER_API_TOKEN` from your private `.env`.
3. Select that credential on each HTTP Request node. Credentials are intentionally not embedded in the exported workflows.
4. Run the research workflow manually. It can take several minutes on CPU; inspect its `errors` field. A successful HTTP status does not mean drafts were generated.
5. Inspect queue and full text:

```sh
docker compose exec worker python app.py list
```

6. Open each original source, verify claims/date/context and check the writing. Approval is a real editorial decision, not a fact-checking algorithm:

```sh
docker compose exec worker python app.py approve POST_ID --note 'Checked original report, date and all claims; edited if needed.'
# Or reject it:
docker compose exec worker python app.py reject POST_ID --note 'Insufficient evidence or repetitive.'
```

To edit a draft, write the complete revised post (including verified source links) to `revised-post.txt`, then run:

```sh
docker compose cp revised-post.txt worker:/data/revised-post.txt
docker compose exec worker python app.py edit POST_ID --text-file /data/revised-post.txt
```

Edits return the post to draft; approve it again after checking. This version has no browser editing dashboard. Publishing/published records cannot be edited this way.

## LinkedIn connection: required before automatic posting

In the `Publish to LinkedIn` node, choose personal-profile post creation, connect your LinkedIn OAuth credential and replace the placeholder Person ID with the identity returned by your authorized connection. The imported credential type may need to be switched to Community Management OAuth2 in your installed n8n version. Use `Share on LinkedIn`/required sign-in products as documented for your app. Some app setup requires an associated Company Page; API availability is not guaranteed by LinkedIn Premium.

Register the exact callback URL displayed by n8n in the LinkedIn developer app. Complete legal agreements/account permissions yourself when required. Do not provide us credentials in chat.

The built-in LinkedIn node varies by n8n version and API access. Its output must expose a returned post URN. If the output shape differs, adjust the **Record receipt** mapping after inspecting a real successful response. It currently accepts `id`, `urn` or `x-restli-id`; a missing URN deliberately leaves the post pending rather than claiming publication.

1. Keep both workflows inactive until all credentials and model settings work.
2. Review and approve ONE real post suitable for publication.
3. Run the publisher manually once. This is a real public post; inspect the text before doing it.
4. Confirm the post on LinkedIn AND its `published` queue record.
5. Enable both workflows only after that test. The publisher needs approved drafts; it will otherwise skip safely.

This version does NOT automatically approve model output. That is intentional during the pilot, because the free RSS/model combination cannot reliably corroborate claims. Fully autonomous editorial selection/approval is future work after quality testing, not a feature to assume exists.

### Uncertain publish result

LinkedIn publishing is not retried automatically. Any reserved post with no recorded receipt blocks later claims. Inspect LinkedIn first. If a post exists, record its actual URN:

```sh
docker compose exec worker python app.py reconcile POST_ID --receipt 'urn:li:share:ACTUAL_ID' --note 'Confirmed on LinkedIn.'
```

Only if you have confirmed no post was created should you return it to draft:

```sh
docker compose exec worker python app.py reconcile POST_ID --note 'Checked LinkedIn; this attempt did not create a post.'
```

Then review/approve again. This trades some unattended uptime for avoiding duplicate posts.

## Use Gemini without extra payment, if eligible

Your annual Gemini subscription is not an API credential. Google's current documentation says subscription developer benefits apply in the AI Studio UI, while direct API access is separately managed/billed.

To use Gemini here without charges, first verify in Google AI Studio that the API key belongs to an eligible **free-tier, unbilled project**, and select a model currently available to that project's free tier. Do not enable Cloud Billing, add prepaid balance or rely on a budget alert as a spending cap. Subscription credits do not automatically make API calls free.

In private `.env` set:

```text
AI_PROVIDER=gemini
GEMINI_MODEL=YOUR_VERIFIED_FREE_TIER_MODEL_ID
GEMINI_API_KEY=YOUR_PRIVATE_KEY
GEMINI_FREE_TIER_CONFIRMED=true
```

Then `docker compose up -d worker`. You can stop Ollama to save resources. When quotas are exhausted or credentials/model access fail, drafting records an error; there is no paid fallback or billing upgrade. The confirmation flag cannot inspect or enforce Google's account billing state. A billed key could incur charges: only connect an actually unbilled free project. Public article excerpts are transmitted to Google when this option is enabled; do not put private messages or personal data into feeds.

If free API eligibility cannot be confirmed, leave `AI_PROVIDER=ollama`. You can still use your paid Gemini app manually for writing without connecting it to n8n.

## Operations and performance

- Research: 8 AM and 6 PM PKT. Publication opportunities: noon and 7 PM PKT. These are test windows, not measured best times for your audience.
- Inspect worker `list`, `docker compose logs --tail 50 worker` and n8n execution failures. There are no external email/SMS alerts configured in this release.
- Record metrics from actual LinkedIn results, ideally at a consistent 24-hour age:

```sh
docker compose exec worker python app.py metrics POST_ID --impressions 100 --comments 3 --reposts 1
```

These numbers are command examples, not your real results. Missing metrics remain unknown. Compare a meaningful sample over 7–14 days; content/format and timing confound each other. Automatic cadence optimization is not implemented.

- Export data: `docker compose exec -T worker python app.py export > content-export.json`
- Consistent private backup: `sh scripts/backup.sh`. It stops writers briefly, copies SQLite and n8n state plus `.env`, then restarts them. Backups contain secrets: protect and store privately off-server.
- Restore: stop services, restore `n8n` directory contents into the n8n volume and `worker` directory contents into the worker volume, restore the same `.env` encryption key, set ownership to the original container users, then start. Test on a separate instance before relying on restore.
- Stop running services: `docker compose stop`. Do not use `down -v` unless intentionally deleting all workflows, content and model data.

## Validation and limits

Run `sh scripts/check.sh` after initialization. Python tests cover URL/date filtering, Atom/RSS parsing, source attachment, model-output link checks, Gemini guard, manual review gating, concurrent reservations, receipts, duplicate prevention, stale stories, daily gap/cap, campaign end and workflow graph structure.

Live feed check on 25 October: BBC returned 3 fresh AI items and Guardian returned 13; Dawn returned an HTTP error and is disabled pending a verified replacement. These counts are transient and do not establish topic trends.

Unit tests are not proof of ongoing feed health, model quality, n8n import compatibility, Oracle availability, LinkedIn permissions, Gemini eligibility, OAuth callback validity or successful publishing. Container/runtime checks must be performed on the actual VPS.

## Official references

- Oracle free resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- n8n Docker: https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose
- n8n LinkedIn node: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.linkedin
- LinkedIn credentials: https://docs.n8n.io/integrations/builtin/credentials/linkedin
- Ollama Docker: https://docs.ollama.com/docker
- Gemini subscription/API distinction: https://ai.google.dev/gemini-api/docs/google-ai-plans
- Gemini API pricing/free models: https://ai.google.dev/gemini-api/docs/pricing
- Docker Ubuntu installation: https://docs.docker.com/engine/install/ubuntu/
