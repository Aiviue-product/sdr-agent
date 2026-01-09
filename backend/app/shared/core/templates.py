# email structure. 

EMAIL_TEMPLATES = {
    "pain_led": {
        "subject": "Question regarding {company_name} ?",
        "body": """
Hi {first_name},

{opening_line}

{f_pain} is a massive headache for many in the {sector} space right now.
Most teams I speak with are trying to move towards {a_goal}, but the gap is real.  

We help teams solve this by {t_solution}. 
Proof: {e_evidence}.

Open to a quick chat to see if this fits?

Best Regards,
Sudev Das (CEO & Founder),
Aiviue.
(https://www.aiviue.com)
"""
    },
    
    "case_reinforcement": {
        "subject": "Hiring in {sector}?",
        "body": """
Hi {first_name},

Following up because {f_pain} is common in {sector} right now.

We usually solve this through {t_solution}, getting teams closer to {a_goal} without the usual overhead.
Recent example: {e_evidence}.

Are you active on the hiring front currently?

Best Regards,
Sudev Das (CEO & Founder),
Aiviue.
(https://www.aiviue.com)
"""
    },
    
    "direct_ask": {
        "subject": "Priority for {company_name}?",
        "body": """
Hi {first_name},

Checking in — not sure if {f_pain} is still a priority for you.

We support {sector} teams specifically with {t_solution}, especially when urgency is {urgency_level}.

Should we reconnect on this or close the loop?

Best Regards,
Sudev Das (CEO & Founder),
Aiviue.
(https://www.aiviue.com) 
"""
    }
}
