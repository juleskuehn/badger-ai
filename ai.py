import openai
import re


def generate_tasks(
    list_name, list=None, num_tasks=10, num_seconds=60, difficulty=1, reflect=False
):
    full_prompt = f"""
Please respond as Badger AI.
Badger AI helps people (end users) accomplish their goals by breaking down themes, concepts or goals into small, actionable steps (action items) which can be done in {num_seconds} seconds or less.
Badger will provide action items that do not require many resources, existing knowledge or time, so that anyone can have a chance to complete them.
Respond only with the action item(s) separated by the pipe character (|). Do not include any other text in your response. Do not number the item(s) or use any other punctuation.\n\n
End user request: Please generate {num_tasks} action item(s) related to {list_name} that can be accomplished in {num_seconds} seconds or less.
"""
    # items = [item.description for item in list.items]
    # if len(items) > 0:
    #     full_prompt += f"\n\nDo not include the following items in your response: {', '.join(exclude)}."
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": full_prompt}],
    )

    response_raw = completion.choices[0].message.content
    response_split = response_raw.split("|")
    response_trimmed = [item.strip() for item in response_split]
    if reflect:
        for i, item in enumerate(response_trimmed):
            full_prompt = f"How long would you estimate the following task to take, in seconds? Respond with the number of seconds only.\n\n{item}"
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": full_prompt}],
            )
            print(
                "Original item:",
                item,
                "\nResponse: ",
                completion.choices[0].message.content,
            )
            # Select the first string of numbers from response with regex
            response_trimmed[i] = {
                "description": response_trimmed[i],
                "seconds": int(
                    re.search(r"\d+", completion.choices[0].message.content).group(0)
                ),
            }
    else:
        response_trimmed = [
            {"description": item, "seconds": 0} for item in response_trimmed
        ]

    return response_trimmed
