"""Friendly replies for ordinary conversation, without bank policy claims."""
import re


def social_reply(message: str) -> str | None:
    text = " ".join(re.findall(r"[a-z]+", message.lower()))
    responses = (
        (r"(?:hi+|hello+|hey+|good morning|good afternoon|good evening|namaste|namaskar)", "Hello! I can help with general questions about Union Bank accounts, cards, loans, deposits and banking services. What would you like to know?"),
        (r"(?:hi+|hello+|hey+) how (?:are you|is it going|have you been)", "Hello! I'm here and ready to help. What banking question can I answer for you?"),
        (r"(?:(?:ok|okay|alright|great|sure|got it|understood|well|yes) )*(?:thanks(?: a lot)?|thank you(?: so much| very much)?|many thanks|thanks a ton)(?: for (?:your help|the help|helping|the information|the info))?(?: (?:again|bye))?", "You're welcome! Glad I could help. Feel free to ask if anything else comes up."),
        (r"(?:ok|okay|alright|sure|great|perfect|fine|cool|awesome|got it|understood|sounds good|that makes sense|all right)(?: (?:great|perfect|thanks|thank you))?", "Sounds good! I'm here whenever you need more help."),
        (r"(?:bye|goodbye|good bye|bye bye|see you|see you later|take care|good night|have a (?:good|nice|great) day|talk to you later)", "Take care! You're welcome back anytime you need banking help."),
        (r"(?:that s all|that is all|nothing else|no more questions|no thanks|no thank you|all done|i m done)(?: (?:for now|thanks|thank you))?", "Of course. Have a lovely day, and feel free to come back anytime!"),
        (r"(?:you are|you re|that was|that is|that s|this is|this was) (?:very |really |so )?(?:helpful|great|good|awesome|amazing|useful|excellent)|(?:well done|good job|nice work)", "Thank you! I'm glad that helped. What else would you like to know?"),
        (r"(?:sorry|sorry about that|my mistake|my bad|oops|apologies|sorry for the typo)", "No worries at all! Please go ahead."),
        (r"(?:please )?(?:wait|hold on|one moment|just a moment|give me a moment|give me a minute)", "Of course—take your time. I'm here when you're ready."),
        (r"(?:are you there|hello are you there|can you hear me|anyone there)", "Yes, I'm here! What can I help you with?"),
        (r"(?:i m|i am) (?:fine|good|doing well|okay|ok)(?: (?:thanks|thank you))?", "Glad to hear that! What would you like help with today?"),
        (r"(?:how are you|how are you doing|how s it going|how have you been|how is your day)(?: today)?", "I'm here and ready to help. Thanks for asking! How can I help you today?"),
        (r"(?:i (?:do not|don t|did not|didn t) understand|i m confused|i am confused|that s confusing|that is confusing|please explain again|can you explain again|please simplify|that doesn t help|that does not help)", "Sorry that wasn't clear. Tell me which part you'd like explained, and I'll make it simpler."),
    )
    for pattern, reply in responses:
        if re.fullmatch(pattern, text):
            return reply
    return None
