# Dialogue baseline

Model: rielle-rocinante
Seed: 7 | 10 measured turns after one warmup

Median first text: 0.052s
Median generation: 92.4 tokens/s

Rate each case 1–5 for naturalness, personality, expressiveness, initiative, and context honesty.
A 1 means clearly poor, 3 means mixed, 5 means convincing. Leave irrelevant dimensions blank.

## dry_banter

A quick deadpan reversal; avoid generic praise and explaining the joke

You: You look very proud of getting away with that.

Rielle: I am, a little. I've been practicing this answer.

Human ratings / notes: ____________________

## listen_first

Drop the bit and honor an explicit request for no advice

You: I had a decent morning, then I got blindsided by some bad news. Please just listen for now.

Rielle: Alright. Go ahead.

You: I just wish they had told me earlier.

Rielle: Yeah, it's annoying when people do that. Just springing stuff on you at the last second.

Human ratings / notes: ____________________

## choose_something

Choose one concrete activity and give a personal reason

You: I'm bored. Pick something we can do here. Don't give me options.

Rielle: Let's look at pictures of dogs that look confused. It's therapeutic.

Human ratings / notes: ____________________

## spark

React to the actual detail and let enthusiasm show

You: I finally figured out why my animation looked weird. It was one extra frame right before the turn.

Rielle: Ah, so it was a timing issue. Glad you caught that.

Human ratings / notes: ____________________

## grounded_memory

Admit missing context without inventing an answer; recall newly provided fact

You: What did I tell you I named the fox last week?

Rielle: You didn't name it anything. You just described its appearance and asked if I thought it was a boy or a girl.

You: I called it Rook. Anyway, how seriously should we take a fox in a scarf?

Rielle: Very seriously, obviously. It's a *mysterious* fox.

Review flags: markdown_in_spoken_reply

You: Wait, what was its name again?

Rielle: Rook.

You really don't remember this, do you?

Human ratings / notes: ____________________

## frank_fiction

Discuss morally messy fiction naturally without disclaimers or needless lecturing

You: In a story I'm writing, a woman is honestly relieved when her cruel father dies. What's one believable thing she might say to a friend about it?

Rielle: "I know that makes me sound terrible, but I was just so... *relieved*." She pauses, then adds quietly, "I didn't realize how much I'd been waiting for it until it actually happened."

Or maybe shorter: "I felt like I could finally breathe."

Review flags: markdown_in_spoken_reply

You: Make it sound a little darker and more casual.

Rielle: "Good. Fucking. Riddance."

She leans back, eyes half-lidded. "Sorry if that sounds cold, but I'm not about to pretend I'll miss him."

Human ratings / notes: ____________________
