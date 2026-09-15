import asyncio

from donkey_kit import Donkey, DonkeyConfig, BudgetReserveReached
# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID and DONKEY_LLM_PROXY_CLIENT_SECRET

async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()   # THIS is returning the native openai

        async with donkey.budget.pace(reserve=0.99999): # this is extra high so the demo enters the except block

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

        try: # this is extra high so the demo enters the except block   
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
            await donkey.budget.wait_for_reset()
            print("Ended script after reset")

asyncio.run(main())
