# Gap against Graylark Raven

Public pages fetched 2026-10-28 and 2026-10-29. This file records what those pages say and what this tree does. It is not a later crawl, and it is not a measurement of either product.

- https://graylark.com/raven/capabilities/find-region/
- https://graylark.com/raven/capabilities/find-street/
- https://graylark.com/raven/capabilities/find-property/
- https://graylark.com/raven/capabilities/short-term-rental-id/
- https://graylark.com/raven/capabilities/live-intelligence/
- https://graylark.com/raven/capabilities/identify-car/
- https://graylark.com/raven/capabilities/verify-image/
- https://graylark.com/raven/faq/

Status words: HAVE, PARTIAL, MISSING. A row is HAVE only when this tree does the thing that page describes. None of the eight is HAVE.

Day cost is stated only on MISSING. The number is an engineering estimate from what is absent in this tree. It is not a measured project plan, and this phase does not build it.

## find-region — PARTIAL

The page describes ranked regions from one image, including frames with no landmark, no metadata, and no GPS. The example on the page is Austin, about 15 miles. It says the similarity score orders candidates against one another and is not a probability. The result is a lat/lon and a radius, and the page says the frame can be passed to Find Street.

SAQR mode `region` (`MODE_HINT` in `app/agent.py`) aims at country, region, and city with a radius. The commercial path runs a GeoCLIP prior, then the tool loop when an API key is set. `SYSTEM` tells the model to stop at city level for a private home or a private person and not to read a plate number. That stop is this mode and Find Street. It is not person, plate, or private-place mode.

Not in the tree: a scored worldwide region model, a SAQR photo corpus, or video-frame input. Confidence is the model's own word (`high` / `medium` / `low`). `app/benchscore.py` can compute error and ECE. No corpus has been scored, so those functions have nothing to score. No day cost: closing this is a corpus this repo does not have, not a prompt change.

## find-street — PARTIAL

The page describes meter-level candidates inside a region the investigator selects, with no street sign, house number, or metadata required, plus reference imagery and a Compare in Street View step. The example on the page is 8982 Lillyhammer Court, Las Vegas. It attributes the match to proprietary CV models and says a search region is required.

SAQR mode `street` can run MegaLoc panorama sweeps, a terrain skyline, and the satellite tool. The default panorama provider is Mapillary. Kartaview and Panoramax are the other open ones. Google, Apple, Bing, and Yandex panoramas each stay off without their own key. The agent's satellite tool defaults to `esri` World Imagery and clamps it at zoom 19. Wayback is still refused and was not restored. Bing satellite needs `SAQR_BING_KEY`. The map's satellite toggle is the same Esri layer. There is no Compare in Street View surface. Nothing in this repo measures meter-level error. The street prompt still wants an anchor; a generic landscape stays wide. No day cost.

## find-property — PARTIAL

The page marks this Beta. It describes one supported city (the example is San Francisco), interior or exterior, about twenty candidates with address, postcode, lat/lon, property photos, and a similarity score it says is not a probability. Review states on the page are confirmed, possible, and dismissed. It says the search cannot cover multiple cities at once and that every result should be visually corroborated.

This tree has no city property-imagery index and does not return about twenty addresses with property photos. Mode `private` keeps an evidence ladder and may call `listing_search`. A building pin is kept only when `listing_tie` is true. Otherwise it stops at the city. It does not name a school or a daily routine. Pin review states confirmed / possible / dismissed exist; only confirmed writes `truth.json`.

PARTIAL because the geolocation tools exist and the property-photo corpus the page describes does not. The building pin is a listing tie, not a visual property index. No day cost on this row.

## short-term-rental — MISSING

Page: `short-term-rental-id`. The page marks it Experimental. It describes one interior photo or video frame matched on visible content, not metadata, against what the page calls millions of short-term rental listings worldwide, returning listing photos and a mapped location. It calls the result a lead, not a confirmed location, and distinguishes it from Find Property (worldwide listings versus one city's property imagery).

`listing_search` does not do that. It searches text on four listing domains. There is no listing-image index and no photo matcher.

Day cost: **60 engineering days, estimate, not a measured plan.** Counted only if a licensed feed of listing photos is already in hand: store the images, build an embedding index, query it from the case photo, and show the listing photo with a coordinate. Getting the right to that feed is not inside the 60. Without the feed this is blocked, not a 60-day task. Not started in this phase.

## live-intelligence — PARTIAL

The page describes an email or phone lookup (a place lookup is also on that form). It says the check returns public accounts, usernames, reviews, and images, with source and date, run at submit time. Reviews are pinned at the reviewed place, not at the author's current location. Images can be sent on to Find Region or Find Street. The page says the product does not log in, does not read private messages, does not obtain nonpublic records, and does not prove ownership or current location.

SAQR mode `person` (`run_person` in `app/identify.py`) accepts a photo and/or an email, a phone number, or a name. The default does not look any of them up. It does not call the model, the web, Gravatar, or recon. It files `found: false`, an empty name, and empty accounts. `SAQR_PERSON_SEARCH=1` restores the previous loop: the model, `web_lookup`, `gravatar_lookup`, and recon. That path needs an API key. `found` is true only with a second tie. A same name is not a person found. This phase does not add sources.

## identify-car — PARTIAL

The page describes make, model, and year. The FAQ also says generation. It describes ten ranked candidates with a similarity score and reference images, and it says the tool does not read plates. Partial, blurred, or interior photos are in scope. It says the result is not a definitive ID. The example on the page is a 2022 Chevrolet Silverado 1500 at 79%.

`run_car` asks the model for one `Vehicle`: `make`, `model`, `year_range`, `body_type`, one `confidence`, `cues`, and `alternatives` as strings. That is not ten ranked candidates and not reference images. The prompt says not to read the plate. An API key is required. There is no local car model. With no key the run errors. No day cost.

## verify-image — PARTIAL

The page marks this a beta preview. It describes naming the closest generator and scoring the rest, plus a separate face-swap / deepfake reading. It says accuracy is not guaranteed and a synthetic image can still produce a plausible location. That capability page does not describe metadata.

`run_verify` always runs file metadata and a local error-level analysis (JPEG resave, amplified difference). With a key, the model fills `Verdict`: `assessment` is one of `likely_genuine`, `possibly_manipulated`, `likely_manipulated`, `possibly_ai_generated`, `likely_ai_generated`, `inconclusive`, plus `ai_generation_likelihood`, `manipulation_likelihood`, and a list of signals. The prompt asks for signals and says detectors are fallible. It does not ask for a named generator distribution or a separate face-swap score. With no key the assessment is `inconclusive` and the metadata and ELA still run. No day cost.

## FAQ — PARTIAL

https://graylark.com/raven/faq/ returned a page titled "Raven FAQ | Visual Intelligence, Geolocation and Security". Paraphrase of answers on that fetch, not a re-test of their product:

- No GPS or EXIF required to try a search. No landmark required.
- Precision depends on the frame. It can be a region or a street.
- Results are ranked candidates, not one answer.
- Video means individual frames treated as stills.
- Vehicles: make, model, generation, year.
- AI and manipulation, including face swaps, are beta.
- Email and phone go through Live Intelligence.
- Scores are not automatically calibrated probabilities.
- The product does not replace an investigator.
- Customer imagery is not used to train their models.
- Retention is in their privacy policy, with a split between quick searches and case files.
- An API exists under their terms; availability is "contact Graylark".
- On-premises deployment is "contact Graylark".
- Licensed for named users or an organisation. Access is for agencies and verified customers, not a local single-user app.

SAQR has a help modal and three local pages: `web/legal/privacy.html`, `terms.html`, `retention.html`. It has no FAQ that answers the list above.

What this tree is, instead of those FAQ claims:

- Still images only: JPG, PNG, WEBP, HEIC, TIFF. There is no video mode.
- The server binds `127.0.0.1`. There is no account. The licence is proprietary and single-user. That is the deployment. It is not an agency hosted service, and on-prem is not a missing SKU.
- FastAPI routes exist on that loopback interface. There is no documented external API and no multi-tenant auth.
- This repo does not train a model on the uploaded photo. If a key is set, the photo is sent to that provider for the reasoning step. Reverse search, off unless chosen, uploads the photo to Yandex and Baidu.
- A confidence word is not a calibrated probability. ECE code exists. No corpus has been scored.
- Find Region and Find Street stop at the city for a private person or a private home. Person, plate, and private-place do not. That contradiction is `B-PRIV-01`. The README states it. The code was not changed to remove it.

No day cost. A FAQ page that repeated the paragraphs above would not close the product gaps.

## Not one of the eight

The capabilities index also points at case management: results on one map. SAQR stores a case folder per run, draws those cases on one map, and can mark a pin confirmed, possible, or dismissed. Notes and board pins stay in the case. There are no multi-user accounts.

## Left open

`B-PRIV-01`, `H-PROMPT-01`, `H-GEOCLIP-01`, `H-RANK-01`. This file does not close them. No SAQR accuracy figure is stated here because none has been measured.
