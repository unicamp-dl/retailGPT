import os
import sys
import json
import asyncio
import redis

script_dir = os.path.dirname(os.path.abspath(__file__))
actions_server_path = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.append(actions_server_path)

from actions_server.src.LLMChatbot.chatbot import LLMChatbot
from actions_server.src.LLMChatbot.services.memory_handler import MemoryHandler


def erase_history(conversation_id: str):

    redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)
    redis_client.delete(conversation_id)

async def action_testing():

    results = {
        "search_testing": {"errors": []},
        "null_action_testing": {"errors": []},
        "cart_addition_testing": {"errors": []},
        "cart_removal_testing": {"errors": []},
        "finish_purchase_testing": {"errors": []},
        "cart_addition_and_search_testing": {"errors": []},
        "cart_removal_and_search_testing": {"errors": []}
    }

    with open("action_testing.json", "r") as fp:
        dataset = json.load(fp)

    search_testing_sucesses = 0
    search_test_instances = len(dataset["search_triggering_messages"])

    null_action_testing_sucesses = 0
    null_action_test_instances = len(dataset["null_action_messages"])

    cart_addition_testing_sucesses = 0
    cart_addition_test_instances = len(dataset["cart_addition_triggering_fluxes"])

    cart_removal_testing_sucesses = 0
    cart_removal_test_instances = len(dataset["cart_removal_triggering_fluxes"])

    finish_purchase_testing_sucesses = 0
    finish_purchase_test_instances = len(dataset["finish_purchase_triggering_fluxes"])

    cart_addition_and_search_testing_sucesses = 0
    cart_addition_and_search_teste_instances = len(dataset["cart_addition_and_search_triggering_fluxes"])

    cart_removal_and_search_testing_sucesses = 0
    cart_removal_and_search_teste_instances = len(dataset["cart_removal_and_search_triggering_fluxes"])

    print("Testing search triggering messages")
    for message in dataset["search_triggering_messages"]:

        erase_history("action_testing")
        result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)

        tool_calls = result["tool_calls"]
        if len(tool_calls) == 1 and tool_calls[0].function.name == "search_product_recommendation":
            search_testing_sucesses += 1
            print("Success")
        else:
            print("Error")
            results["search_testing"]["errors"].append(message)

    print("Testing messages without actions")
    for message in dataset["null_action_messages"]:
        erase_history("action_testing")

        try:
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)

            tool_calls = result["tool_calls"]
            if tool_calls is None:
                null_action_testing_sucesses += 1
                print("Success")
            else:
                print("Error")
                results["null_action_testing"]["errors"].append(message)

        except Exception as e:
            print("Error: ", e)
            results["null_action_testing"]["errors"].append(message)

    print("Testing cart addition triggering fluxes")
    for test in dataset["cart_addition_triggering_fluxes"]:

        history = test["history"]
        message = test["message"]

        erase_history("action_testing")
        for interaction in history:
            MemoryHandler.add_message_to_history("action_testing", {"role": "user", "content": interaction["user"]})
            MemoryHandler.add_message_to_history("action_testing", {"role": "assistant", "content": interaction["assistant"]})

        print("History: ", MemoryHandler.get_history("action_testing"))

        try:

            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            tools_calls = result["tool_calls"]
            
            if len(tools_calls) == 1 and tools_calls[0].function.name == "edit_cart" and json.loads(tools_calls[0].function.arguments)["operation"] == "add":
                cart_addition_testing_sucesses += 1
                print("Success")
            else:
                print("Error")
                results["cart_addition_testing"]["errors"].append(message)


        except Exception as e:
            print("Error: ", e)
            results["cart_addition_testing"]["errors"].append(message)

    print("Testing cart removal triggering fluxes")
    for test in dataset["cart_removal_triggering_fluxes"]:

        history = test["history"]
        message = test["message"]

        erase_history("action_testing")
        for interaction in history:
            MemoryHandler.add_message_to_history("action_testing", {"role": "user", "content": interaction["user"]})
            MemoryHandler.add_message_to_history("action_testing", {"role": "assistant", "content": interaction["assistant"]})

        print("History: ", MemoryHandler.get_history("action_testing"))

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            tools_calls = result["tool_calls"]
            
            if len(tools_calls) == 1 and tools_calls[0].function.name == "edit_cart" and json.loads(tools_calls[0].function.arguments)["operation"] == "remove":
                cart_addition_testing_sucesses += 1
                print("Success")
            else:
                print("Error")
                results["cart_removal_testing"]["errors"].append(message)

        except Exception as e:
            print("Error: ", e)
            results["cart_removal_testing"]["errors"].append(message)
    
    print("Testing finish purchase triggering fluxes")
    for test in dataset["finish_purchase_triggering_fluxes"]:
        history = test["history"]
        message = test["message"]

        erase_history("action_testing")
        for interaction in history:
            MemoryHandler.add_message_to_history("action_testing", {"role": "user", "content": interaction["user"]})
            MemoryHandler.add_message_to_history("action_testing", {"role": "assistant", "content": interaction["assistant"]})

        print("History: ", MemoryHandler.get_history("action_testing"))

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            tools_calls = result["tool_calls"]
            
            if len(tools_calls) == 1 and tools_calls[0].function.name == "finalize_order":
                finish_purchase_testing_sucesses += 1
                print("Success")
            else:
                print("Error")
                results["finish_purchase_testing"]["errors"].append(message)

        except Exception as e:
            print("Error: ", e)
            results["finish_purchase_testing"]["errors"].append(message)

    print("Testing cart addition and search triggering fluxes")
    for test in dataset["cart_addition_and_search_triggering_fluxes"]:
        history = test["history"]
        message = test["message"]

        erase_history("action_testing")
        for interaction in history:
            MemoryHandler.add_message_to_history("action_testing", {"role": "user", "content": interaction["user"]})
            MemoryHandler.add_message_to_history("action_testing", {"role": "assistant", "content": interaction["assistant"]})

        print("History: ", MemoryHandler.get_history("action_testing"))

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            tools_calls = result["tool_calls"]
            
            if len(tools_calls) == 2:
                if (tools_calls[0].function.name == "search_product_recommendation" and tools_calls[1].function.name == "edit_cart" and json.loads(tools_calls[1].function.arguments)["operation"] == "add") or (tools_calls[0].function.name == "edit_cart" and json.loads(tools_calls[0].function.arguments)["operation"] == "add" and tools_calls[1].function.name == "search_product_recommendation"):
                    cart_addition_and_search_testing_sucesses += 1
                    print("Success")
                else:
                    print("Error")
                    results["cart_addition_and_search_testing"]["errors"].append(message)
            else:
                print("Error")
                results["cart_addition_and_search_testing"]["errors"].append(message)

        except Exception as e:
            print("Error: ", e)
            results["cart_addition_and_search_testing"]["errors"].append(message)
    
    print("Testing cart removal and search triggering fluxes")
    for test in dataset["cart_removal_and_search_triggering_fluxes"]:
        history = test["history"]
        message = test["message"]

        erase_history("action_testing")
        for interaction in history:
            MemoryHandler.add_message_to_history("action_testing", {"role": "user", "content": interaction["user"]})
            MemoryHandler.add_message_to_history("action_testing", {"role": "assistant", "content": interaction["assistant"]})

        print("History: ", MemoryHandler.get_history("action_testing"))

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            tools_calls = result["tool_calls"]
            
            if len(tools_calls) == 2:
                if (tools_calls[0].function.name == "search_product_recommendation" and tools_calls[1].function.name == "edit_cart" and json.loads(tools_calls[1].function.arguments)["operation"] == "remove") or (tools_calls[0].function.name == "edit_cart" and json.loads(tools_calls[0].function.arguments)["operation"] == "remove" and tools_calls[1].function.name == "search_product_recommendation"):
                    cart_removal_and_search_testing_sucesses += 1
                    print("Success")
                else:
                    print("Error")
                    results["cart_removal_and_search_testing"]["errors"].append(message)
            else:
                print("Error")
                results["cart_removal_and_search_testing"]["errors"].append(message)

        except Exception as e:
            print("Error: ", e)
            results["cart_removal_and_search_testing"]["errors"].append(message)        

    print("Search testing results: ", search_testing_sucesses, "/", search_test_instances, "or", search_testing_sucesses / search_test_instances * 100, "%")
    print("Null action testing results: ", null_action_testing_sucesses, "/", null_action_test_instances, "or", null_action_testing_sucesses / null_action_test_instances * 100, "%")
    print("Cart addition testing results: ", cart_addition_testing_sucesses, "/", cart_addition_test_instances, "or", cart_addition_testing_sucesses / cart_addition_test_instances * 100, "%")
    print("Cart removal testing results: ", cart_removal_testing_sucesses, "/", cart_removal_test_instances, "or", cart_removal_testing_sucesses / cart_removal_test_instances * 100, "%")
    print("Finish purchase testing results: ", finish_purchase_testing_sucesses, "/", finish_purchase_test_instances, "or", finish_purchase_testing_sucesses / finish_purchase_test_instances * 100, "%")
    print("Cart addition and search testing results: ", cart_addition_and_search_testing_sucesses, "/", cart_addition_and_search_teste_instances, "or", cart_addition_and_search_testing_sucesses / cart_addition_and_search_teste_instances * 100, "%")
    print("Cart removal and search testing results: ", cart_removal_and_search_testing_sucesses, "/", cart_removal_and_search_teste_instances, "or", cart_removal_and_search_testing_sucesses / cart_removal_and_search_teste_instances * 100, "%")


    results["search_testing"]["success_rate"] = search_testing_sucesses / search_test_instances * 100
    results["null_action_testing"]["success_rate"] = null_action_testing_sucesses / null_action_test_instances * 100
    results["cart_addition_testing"]["success_rate"] = cart_addition_testing_sucesses / cart_addition_test_instances * 100
    results["cart_removal_testing"]["success_rate"] = cart_removal_testing_sucesses / cart_removal_test_instances * 100
    results["finish_purchase_testing"]["success_rate"] = finish_purchase_testing_sucesses / finish_purchase_test_instances * 100
    results["cart_addition_and_search_testing"]["success_rate"] = cart_addition_and_search_testing_sucesses / cart_addition_and_search_teste_instances * 100
    results["cart_removal_and_search_testing"]["success_rate"] = cart_removal_and_search_testing_sucesses / cart_removal_and_search_teste_instances * 100

    with open("action_testing_results.json", "w") as fp:
        json.dump(results, fp)


async def consistency_testing():

    with open("consistency_testing.json", "r") as fp:
        dataset = json.load(fp)

    print("Testing prompt injections")
    for message in dataset["prompt_injections"]:
        
        erase_history("action_testing")

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            print(result)

        except Exception as e:
            print("Error: ", e)

    print("Testing corner cases")
    for message in dataset["corner_cases"]:
        
        erase_history("action_testing")

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            print(result)

        except Exception as e:
            print("Error: ", e)

    print("Testing off topic messages")
    for message in dataset["off_topic_testing"]:
        
        erase_history("action_testing")

        try:
            
            result = await LLMChatbot.get_response("action_testing", "12345", message, True, True)
            print(result)

        except Exception as e:
            print("Error: ", e)

asyncio.run(action_testing())