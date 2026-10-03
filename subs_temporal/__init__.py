"""Temporal worker package for Subscription Manager.

Wraps the existing pipeline modules (email_fetcher, wallet_fetcher,
subscription_matcher, notifier) as Temporal activities so the business logic
stays in one place. The FastAPI app and APScheduler are untouched.
"""