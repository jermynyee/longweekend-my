To: affiliate@klook.com
From: hello@longweekend.my
Subject: Deep-link hotel search with check-in / check-out date params

Hi Klook Affiliate team,

Quick technical question. We run a Malaysian long-weekend planner
(longweekend.my) and send users to Klook hotels from each trip card.
Our current links look like:

  https://affiliate.klook.com/redirect?aid=126213&aff_adid=1326747
    &k_site=https%3A%2F%2Fwww.klook.com%2Fhotels%2F%3Fsearch_query%3DPenang

This pre-fills "Penang" on the hotel search page, but the user still
has to pick check-in and check-out dates manually. A typical trip
from our site is 3-5 days.

For comparison, Booking.com accepts checkin=YYYY-MM-DD&checkout=YYYY-MM-DD
on searchresults.html, and Agoda accepts checkIn=YYYY-MM-DD&checkOut=YYYY-MM-DD
on /search. We currently route to Klook because it's the only working
affiliate, but the missing date pre-fill hurts conversion.

Two questions:

  1. Does the Klook hotel search page accept check-in / check-out
     parameters via URL? If yes, what's the exact param name(s),
     accepted date format, and an example URL?

  2. If this isn't a public feature, is there an undocumented
     deep-link parameter set available to registered affiliates?
     We're ID 126213.

Concrete example of what we'd send a user clicking a "long weekend
in Penang" card for Sat 25 Aug – Wed 29 Aug:

  https://affiliate.klook.com/redirect?aid=126213&aff_adid=1326747
    &k_site=https%3A%2F%2Fwww.klook.com%2Fhotels%2F%3Fsearch_query%3DPenang
    %26checkin%3D2025-08-25%26checkout%3D2025-08-29

Even a "no, not currently supported" is useful — saves us chasing
ghosts. If the answer is yes, we'd implement the same day.

Thanks,
longweekend.my
