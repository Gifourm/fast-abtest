import asyncio

from fast_abtest import ab_test
from fast_abtest import Metric


main_c = 0
b_c = 0
c_c = 0


@ab_test(metrics=[Metric.LATENCY])
async def main_scenario(a: int, b: str) -> None:
    global main_c
    main_c += 1


@main_scenario.register_variant(traffic_percent=33)
async def scenario_b(a: int, b: str) -> None:
    global b_c
    b_c += 1


@main_scenario.register_variant(traffic_percent=33)
async def scenario_c(a: int, b: str) -> None:
    global c_c
    print(f"C scenario")
    c_c += 1


async def main():
    # scenario_c(4, "1r")
    for i in range(10000):
        await main_scenario(123, "asfg")

    print(main_c)
    print(b_c)
    print(c_c)


# asyncio.run(main())
