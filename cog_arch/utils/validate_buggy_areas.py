import json

from pathlib import Path
from loguru import logger

from langchain_core.messages import HumanMessage

from app.inference import search_for_bug_location
from app.log import print_acr, print_banner


def validate_buggy_areas(state, output_dir, api_manager, print_callback):
    res_text = state['info']
    round_no = state['start_round_no']
    msg_thread = state['msg_thread']

    selected_apis, _, proxy_threads = api_manager.proxy_apis(res_text)

    proxy_log = Path(output_dir, f"agent_proxy_{round_no}.json")
    proxy_messages = [thread.to_msg() for thread in proxy_threads]
    proxy_log.write_text(json.dumps(proxy_messages, indent=4))

    if selected_apis is None:
        msg = "Invalid buggy areas"
        print_acr(
            msg,
            f"context retrieval round {round_no}",
            print_callback=print_callback,
        )
        return {"valid_buggy_areas": False, "buggy_area_msg": msg}

    selected_apis_json = json.loads(selected_apis)

    buggy_locations = selected_apis_json.get("bug_locations", [])

    formatted = []

    if buggy_locations:
        formatted.append("\n\nBug locations")
        for location in buggy_locations:
            s = ", ".join(f"{k}: `{v}`" for k, v in location.items())
            formatted.extend([f"\n- {s}"])

    print_acr(
        "\n".join(formatted),
        "Agent-selected API calls",
        print_callback=print_callback,
    )

    # collected enough information to write patch
    if buggy_locations:
        collated_tool_response = "Here is the code in buggy locations:\n\n"
        # provide the buggy locations to the model
        for bug_location in buggy_locations:
            tool_output, *_ = search_for_bug_location(
                api_manager, msg_thread, bug_location
            )
            collated_tool_response += f"\n\n{tool_output}\n"

        if (
                "Unknown function" not in collated_tool_response
                and "Could not" not in collated_tool_response
        ):

            print_banner("PATCH GENERATION")
            logger.debug("Gathered enough information. Invoking write_patch.")
            print_acr(
                collated_tool_response,
                "patch generation round 1",
                print_callback=print_callback,
            )

            return {"valid_buggy_areas": True, "buggy_area_msg": collated_tool_response}

    msg = "The buggy locations is not precise. You may need to check whether the arguments are correct and search more information."

    print_acr(
        msg,
        f"context retrieval round {round_no}",
        print_callback=print_callback,
    )
    return {"valid_buggy_areas": False, "buggy_area_msg": msg}


def buggy_area_router(state):
    if not state['valid_buggy_areas']:
        state["messages"] += [HumanMessage(content=state['buggy_area_msg'])]
        return "agent"
    return "write_patch"
