import asyncio

import httpx
from donkey_kit import BudgetReserveReached, Donkey
from donkey_kit.core.budget import LIMIT_HEADER, REMAINING_HEADER, RESET_HEADER

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID and DONKEY_LLM_PROXY_CLIENT_SECRET

async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()   # THIS is returning the native openai

        # First call is unobserved, so pace lets it through and the window arrives
        # in-band. reserve=0.99999 means "keep almost the whole window" — any
        # observed usage trips the second call.
        async with donkey.budget.pace(reserve=0.99999):

            response = await client.responses.create(
                model="gpt-4o",
                input="Say hello in exactly three words.",
            )

            print("request 1 response is", response.output_text)
            budget = donkey.budget

            print("after request 1, budget remaining is", budget.remaining)
            print("after request 1, budget limit is", budget.limit)
            print("after request 1, budget observed_at is", budget.observed_at)
            print("after request 1, budget fraction_used is", budget.fraction_used)
            print("after request 1, budget reset is", budget.reset_at)

        try:
            async with donkey.budget.pace(reserve=0.99999):
                response = await client.responses.create(
                    model="gpt-4o",
                    input="Say hello in exactly three words.",
                )

                print("after request 2, budget remaining is", budget.remaining)
                print("after request 2, budget limit is", budget.limit)
                print("after request 2, budget observed_at is", budget.observed_at)
                print("after request 2, budget fraction_used is", budget.fraction_used)
                print("after request 2, budget reset is", budget.reset_at)

        except BudgetReserveReached as exc:
            print("after BudgetReserveReached, budget remaining is", budget.remaining)
            print("after BudgetReserveReached, budget limit is", budget.limit)
            print("after BudgetReserveReached, budget observed_at is", budget.observed_at)
            print("after BudgetReserveReached, budget fraction_used is", budget.fraction_used)
            print("after BudgetReserveReached, budget reset is", budget.reset_at)
            print("--------------------------------")
            print("stopped locally [in-script]", exc.fraction_used, exc.reserve)
            # wait_for_reset sleeps until reset_at. Observe a 1s window so this
            # does not sit on the live/simulator reset (often minutes).
            donkey.budget.observe(
                httpx.Response(
                    200,
                    headers={
                        LIMIT_HEADER: "100000",
                        REMAINING_HEADER: "4000",
                        RESET_HEADER: "1000",
                    },
                )
            )
            await donkey.budget.wait_for_reset()
            print("Ended script after reset")

asyncio.run(main())
