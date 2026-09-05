# I'm a data analyst, not a developer. I built a working app in an afternoon anyway.
## How AI coding tools are changing what "building something" means for people like me.

---

There's a gap I've always felt between understanding data and actually building things.

I spend my days in analytics — I know how APIs work, I understand data pipelines, I can write SQL in my sleep. But shipping a working web app, writing Python scripts, setting up automated jobs? That always felt like it belonged to a different kind of person.

This summer I closed that gap. Not because I learned to code. Because I stopped needing to.

## The problem

My son started a new school year and I kept missing things — assignments due, readings posted, deadlines quietly approaching. His school uses Canvas, an LMS that has all of this information, but the interface isn't built for parents checking in from a phone at 9 PM.

I wanted a single page I could open that would show me everything coming up, color-coded by urgency, with clickable links. And I wanted it emailed to me every evening without me having to think about it.

## The build

I opened Claude and described what I wanted. Within an hour I had a Python script that called the Canvas API, pulled every assignment across all courses, and generated a styled HTML dashboard. It sorted assignments into buckets — due today, this week, coming up — and color-coded them red, yellow, green.

Then I asked for an email digest. Then password protection on the web page. Then automatic daily scheduling. Each request took minutes, not days.

What struck me wasn't just the speed. It was that I could reason about the code. I'm not a developer, but I understand data — and reading API calls, conditional logic, and HTML templates isn't foreign to me when they're written cleanly and I can ask questions about them. Claude didn't just write code. It wrote code I could understand, debug, and own.

## What I ended up with

- A live dashboard at a GitHub Pages URL, updated every day
- Password protection so I can share the link with family
- A daily 6 PM email with every upcoming assignment, a "View Dashboard" button, and the password included
- The whole thing runs automatically on my son's computer — I never have to touch it

## What this means

I've been in analytics long enough to know that the hardest part of data work isn't the analysis — it's getting the data into a shape where you can act on it. Developers build the pipes; analysts use them.

AI coding tools are collapsing that distinction. Not because they replace developers — they don't — but because they let people who understand problems, data, and logic actually ship solutions without a six-month detour through a bootcamp.

I'm not a developer. But I built something real, that my family uses every day, that solves an actual problem. That feels like a new kind of capability — and I'm just getting started with it.

---

*The full source code is on [GitHub](https://github.com/rashmirammurthy-debug/canvas-dashboard). If you have a kid on Canvas and want to set this up, the README walks through it.*
