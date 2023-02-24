# Karma bot BLAGO 🙏🏻

## Description

BLAGO 🙏🏻 is a Telegram bot which manages people's karma. Karma is essentially just a number of points assigned to a user. It could be either increased or decreased for whatever reason.
Thus, the bot acts as an arbitrator within a group of people providing ability for such groups to manage their own ecosystem of karma. Which overall leads to an ultimate BLAGO 🙏🏻

## Bot commands

* `/help` - displays all available commands with their description
* `/up [reason]` - request +1 KS (Karma score) for a member (an optional reason could be set)
* `/down [reason]` - request -1 KS for a member (an optional reason could be set)
* `/show [user_mention]` - show a list of all memebers with their KS (or only for mentioned member)

## Install

1. Create your instance of Telegram bot using [@BotFather](https://telegram.me/BotFather) and obtain bot token. For example, follow the instructions [here](https://core.telegram.org/bots#how-do-i-create-a-bot)

2. Install Python 3 dependencies:
```
pip install -r requirements.txt
```

3. Export environment variable with the bot token value obtained in step 1:
```
export TELEGRAM_BOT_TOKEN=<bot_token>
```

4. Run the bot:
```
python3 -m main.py
```

## Deployment

1. Install Python 3 dependencies into `vendor/python` directory:
```
pip install -r requirements.txt -t vendor/python
```

2. Remove `asyncio` package from the vendor directory (since AWS has its own version pre-installed the local version might cause conflicts):
```
rm -rf vendor/python/asyncio
```

3. Install [Serverless](https://www.serverless.com/) framework and its required plugins:
```
npm install -g serverless serverless-dotenv-plugin
```

4. Create AWS config which will be used to deply the bot:
```
aws configure set aws_access_key_id <aws_access_key_id> --profile blago_karma_bot
aws configure set aws_secret_access_key <aws_secret_access_key> --profile blago_karma_bot
```

5. Deploy the bot using [Serverless](https://www.serverless.com/) framework:
```
serverless deploy
```

6. Use the following command to setup Telegram webhook for the deployed lambda function:
```
curl --request POST --url https://api.telegram.org/bot<bot_token>/setWebhook --header 'content-type: application/json' --data '{"url": "<aws_lambda_url"}'
```

## Clean up

1. Delete Telegram webhook using the following command:
```
curl --request POST --url https://api.telegram.org/bot<bot_token>/setWebhook\?remove
```

2. Remove deployed bot using [Serverless](https://www.serverless.com/) framework:
```
serverless remove
```

## Voting rules

* Requestor cannot send Karma changing request for himself/herself 
* In order to successfully change person's KS, the request should be confirmed by a third member
* Requestor cannot confirm the request, but can reject it
* Requested person cannot neither confirm nor reject the request
* After the timeout (*1 minute* by default) it becomes impossible to select a memeber for the request
* After the timeout (*10 hours* by default) the request becomes invalid

## Environment variables

TBD