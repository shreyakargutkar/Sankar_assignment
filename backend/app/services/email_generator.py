import json
from typing import Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.models.influencer import Influencer
from app.models.outreach import OutreachCampaign

try:
    import anthropic
except ImportError:
    anthropic = None


SEQUENCE_LABELS = {
    0: "initial cold outreach",
    1: "first polite follow-up",
    2: "final follow-up",
}


class EmailGenerator:
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.client = None
        if self.api_key and anthropic:
            try:
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client for email generation: {e}")

    def is_api_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def build_opt_out_footer(self, sender_name: str, opt_out_url: str, sender_email: str = "") -> str:
        sender = f"{sender_name} <{sender_email}>" if sender_email else sender_name
        return (
            f"\n\n---\n"
            f"Sender: {sender}\n"
            f"This message is a professional collaboration inquiry. "
            f"If you would prefer not to receive further emails, reply STOP or use this opt-out link: {opt_out_url}"
        )

    async def generate_email(
        self,
        influencer: Influencer,
        campaign: OutreachCampaign,
        sequence_number: int,
        opt_out_url: str,
        sender_email: str = "",
    ) -> Dict[str, str]:
        if settings.ANTHROPIC_API_KEY and not settings.DEMO_MODE:
            if not self.client:
                raise RuntimeError("Claude email generation is configured but its client is unavailable.")
            draft = await self._generate_with_claude(
                influencer, campaign, sequence_number, sender_email
            )
        else:
            draft = self._simulate_email(influencer, campaign, sequence_number, sender_email)

        if not draft.get("subject", "").strip() or not draft.get("body", "").strip():
            raise ValueError("Email generation returned an empty subject or body.")
        footer = self.build_opt_out_footer(campaign.sender_name, opt_out_url, sender_email)
        draft["body"] = draft["body"].rstrip() + footer
        return draft

    async def _generate_with_claude(
        self,
        influencer: Influencer,
        campaign: OutreachCampaign,
        sequence_number: int,
        sender_email: str,
    ) -> Dict[str, str]:
        why = influencer.match_reason or (
            f"Their {influencer.niche} audience of {influencer.followers_count:,} followers in {influencer.location} "
            f"aligns with the campaign."
        )
        prompt = f"""
You write concise, professional influencer partnership emails. Produce a {SEQUENCE_LABELS.get(sequence_number, 'outreach')} email.

Brand: {campaign.brand_name}
Campaign: {campaign.campaign_description}
Collaboration opportunity: {campaign.collaboration_offer}
Call to action: {campaign.call_to_action}
Sender name: {campaign.sender_name}
Sender email (for identification): {sender_email or 'to be filled by Gmail account'}

Influencer:
- Name: {influencer.name}
- Handle: @{influencer.instagram_username}
- Niche: {influencer.niche}
- Followers: {influencer.followers_count}
- Location: {influencer.location}
- Why selected: {why}
- AI summary: {influencer.profile_summary or 'n/a'}

Rules:
- Introduce the brand clearly.
- Explain the collaboration opportunity.
- Mention why this influencer was selected (specific, not generic flattery).
- Include a clear call to action.
- Identify the sender by name.
- Keep a respectful tone. No spammy language, ALL CAPS, or excessive punctuation.
- If this is a follow-up, briefly reference the previous note without guilt-tripping.
- Do not include an opt-out footer; the application appends the required sender and opt-out details.
- Return ONLY JSON: {{"subject": "...", "body": "..."}}
- Body should be plain text, 120-220 words.
"""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=700,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)
        return {
            "subject": str(data.get("subject", f"Collaboration with {campaign.brand_name}")).strip(),
            "body": str(data.get("body", "")).strip(),
        }

    def _simulate_email(
        self,
        influencer: Influencer,
        campaign: OutreachCampaign,
        sequence_number: int,
        sender_email: str,
    ) -> Dict[str, str]:
        why = influencer.match_reason or (
            f"your {influencer.niche.lower()} content and {influencer.followers_count:,}-follower community in {influencer.location}"
        )
        first = influencer.name.split()[0]
        sender = campaign.sender_name
        brand = campaign.brand_name
        offer = campaign.collaboration_offer or "a paid collaboration with creative control"
        cta = campaign.call_to_action or "Reply to this email if you would like to review a brief."
        identity = f"{sender}" + (f" ({sender_email})" if sender_email else "")

        if sequence_number == 0:
            subject = f"{first}, collaboration idea from {brand}"
            body = (
                f"Hi {first},\n\n"
                f"I'm {identity} with {brand}. {campaign.campaign_description.strip()}\n\n"
                f"We would like to explore {offer} with you. You were selected because {why} "
                f"That combination is a strong fit for an authentic partnership rather than a generic shout-out.\n\n"
                f"{cta}\n\n"
                f"If this is not relevant, you can ignore this note or opt out using the link below — we will stop follow-ups immediately.\n\n"
                f"Best regards,\n{sender}\n{brand}"
            )
        elif sequence_number == 1:
            subject = f"Following up — {brand} x @{influencer.instagram_username}"
            body = (
                f"Hi {first},\n\n"
                f"I wanted to follow up on my previous note from {identity} at {brand}. "
                f"We are still interested in {offer} because of {why}\n\n"
                f"{cta}\n\n"
                f"If you are not interested, reply “not interested” or use the opt-out link and we will close this thread.\n\n"
                f"Thank you,\n{sender}\n{brand}"
            )
        else:
            subject = f"Last note from {brand} — happy to close the loop"
            body = (
                f"Hi {first},\n\n"
                f"This is a final follow-up from {identity} at {brand} about a possible collaboration. "
                f"We reached out because {why}. If the timing is better later, we are glad to pause. "
                f"If you are open to {offer}, {cta}\n\n"
                f"Otherwise we will not send further emails about this campaign.\n\n"
                f"Kind regards,\n{sender}\n{brand}"
            )
        return {"subject": subject, "body": body}


email_generator = EmailGenerator()
