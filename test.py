import logging
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import pandas as pd

# Set up logging first
try:
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
except Exception as e:
    print(f"Failed to initialize logging: {e}")
    raise

# Load environment variables
try:
    load_dotenv()
    if "SLACK_BOT_TOKEN" not in os.environ or "SLACK_APP_TOKEN" not in os.environ:
        raise ValueError("Required environment variables SLACK_BOT_TOKEN and/or SLACK_APP_TOKEN not found")
    logger.debug("Bot Token: %s...%s", os.environ["SLACK_BOT_TOKEN"][:10], os.environ["SLACK_BOT_TOKEN"][-5:])
    logger.debug("App Token: %s...%s", os.environ["SLACK_APP_TOKEN"][:10], os.environ["SLACK_APP_TOKEN"][-5:])
except Exception as e:
    logger.critical(f"Failed to load environment variables: {e}")
    raise


# Initialize the app
try:
    app = App(token=os.environ["SLACK_BOT_TOKEN"])
except Exception as e:
    logger.critical(f"Failed to initialize Slack app: {e}")
    raise


# Event handler for when the bot is mentioned in a channel
@app.event("app_mention")
def event_test(event, say, logger):
    try:
        logger.info(f"Received mention event: {event}")
        say(f"Hi there, <@{event['user']}>! :wave:")
    except KeyError as e:
        logger.error(f"Missing required field in event data: {e}")
        say("Sorry, I encountered an error processing your mention.")
    except Exception as e:
        logger.error(f"Error handling mention event: {e}")
        say("Sorry, something went wrong while processing your mention.")

# @app.command("/help")
# def help_command(ack, body, logger):
#     ack("This is a help command")

@app.event("message")
def handle_message_events(event, say, client, logger):
    try:
        # Ignore bot messages, bot mentions, messages without text, and mentions of this bot
        if (
            event.get("bot_id") or 
            event.get("subtype") == "bot_message" or 
            "text" not in event or
            event.get("user") == app.client.auth_test()["user_id"] or
            f"<@{app.client.auth_test()['user_id']}>" in event.get("text", "")
        ):
            return

        # Check if the message is from channel A (use actual channel ID)
        if event.get("channel") == "C084RT6DWUB" or event.get("type") == "app_mention":  # Replace with your channel A ID
            logger.info(f"Received message in channel A: {event}")
            
            try:
                # If this is a new message (not in a thread), start a thread
                thread_ts = event.get('thread_ts')
                if not thread_ts:
                    # Reply in a thread to the original message
                    thread_response = client.chat_postMessage(
                        channel=event['channel'],
                        thread_ts=event['ts'],
                        text="I'll help route this message. Starting a thread for our conversation."
                    )
                    thread_ts = event['ts']

                # Check for user mentions in the message
                message_text = event.get('text', '')
                mentioned_users = [user_id.strip('<@>') for user_id in message_text.split() if user_id.startswith('<@') and user_id.endswith('>')]
                
                # Send DM to mentioned users
                for user_id in mentioned_users:
                    try:
                        client.chat_postMessage(
                            channel=user_id,
                            text=f"You were mentioned in <#{event['channel']}>:\n{message_text}\n\n<{client.chat_getPermalink(channel=event['channel'], message_ts=thread_ts)['permalink']}|View thread>"
                        )
                        logger.info(f"Sent DM to user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send DM to user {user_id}: {e}")

                # Post the message to channel B (use actual channel ID)
                result = client.chat_postMessage(
                    channel="C0854LP1ZMX",  # Replace with your channel B ID
                    text=f"Message forwarded from <#{event['channel']}> by <@{event['user']}>:\n{event['text']}\n\n<{client.chat_getPermalink(channel=event['channel'], message_ts=thread_ts)['permalink']}|View thread>",
                    unfurl_links=True
                )
                logger.info(f"Message successfully routed to channel B: {result}")
                
                # Acknowledge in original channel's thread
                say(
                    text="Your message has been routed to the appropriate channel. Thank you for your patience. If you are not satisfied with the response, please choose one of the options below.",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Your message has been routed to the appropriate channel. Thank you for your patience. If you are not satisfied with the response, please choose one of the options below."
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Contact Shift Manager"
                                    },
                                    "value": "U085AD2V456",  # Just the ID without <@ >
                                    "action_id": "contact_shift_manager"
                                },
                                {
                                    "type": "button", 
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Contact Ticket Owner"
                                    },
                                    "action_id": "contact_ticket_owner"
                                }
                            ]
                        }
                    ],
                    thread_ts=thread_ts
                )
                
            except Exception as e:
                logger.error(f"Error routing message: {e}")
                say(
                    text="Sorry, there was an error routing your message. Please try again later.",
                    thread_ts=thread_ts if thread_ts else event['ts']
                )
                
    except Exception as e:
        logger.error(f"Error processing message event: {e}")
        try:
            say(
                text="Sorry, an unexpected error occurred while processing your message.",
                thread_ts=event.get('thread_ts', event.get('ts'))
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")

# Add action handler for Contact Shift Manager button
@app.action("contact_shift_manager")
def handle_shift_manager_action(ack, body, client, logger):
    ack()
    try:
        # Get the original message's thread_ts and channel from the body
        thread_ts = body["message"]["thread_ts"] if "thread_ts" in body["message"] else body["message"]["ts"]
        channel_id = body["channel"]["id"]
        shift_manager_id = body["actions"][0]["value"]
        
        # Log the values we're using
        logger.debug(f"thread_ts: {thread_ts}")
        logger.debug(f"channel_id: {channel_id}")
        logger.debug(f"shift_manager_id: {shift_manager_id}")

        # Try to get user info to verify the ID is valid
        try:
            user_info = client.users_info(user=shift_manager_id)
            logger.debug(f"User info retrieved: {user_info}")
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")

        # Send DM to shift manager with @mention to trigger notification
        dm_result = client.chat_postMessage(
            channel=shift_manager_id,
            text=f"<@{shift_manager_id}> You've been contacted as the Shift Manager regarding this thread:\n<{client.chat_getPermalink(channel=channel_id, message_ts=thread_ts)['permalink']}|View thread>"
        )
        logger.debug(f"DM send result: {dm_result}")
        
        # Confirm in thread that shift manager was notified
        thread_result = client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"I've notified the Shift Manager <@{shift_manager_id}>"
        )
        logger.debug(f"Thread confirmation result: {thread_result}")
        logger.info(f"Sent notification to shift manager {shift_manager_id}")
    except Exception as e:
        logger.error(f"Failed to contact shift manager: {e}", exc_info=True)

                        
if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {e}")
        raise