:og:description: Axobot has a very cool and unique scam detection feature. This article explains how that massive thing technically works.

====================
Axobot scam detector
====================

As Discord becomes an increasingly important social network, attracting hundreds of new users worldwide every day, it is naturally subject to more and more phishing and other scams. Developers are already reacting to this plague, such as by buying a cybersecurity company or adding new auto-moderation and reporting features, but scams are becoming more sophisticated and affecting many users all the time.

As the Axobot developer and a CS student, I think it’s important to try to limit the spread of these scams as much as possible. That’s why I decided several months ago to work on an AI able to detect scams among the thousands of messages read by Axobot every hour, so as to be able to warn the moderators of the affected servers and take the necessary actions.

This page is not about how you will use this new feature in Axobot, but rather about how I reached this result from a technical point of view and what it entails.


----------
The Basics
----------

Scams in Discord are a very specific category of scams, fortunately easy to isolate. They are mainly fake links that look like the official websites of Discord, Steam or Epic Games, as well as offers for free PayPal accounts or Nitro subscriptions. There are also scams offering “ friends ” to download malicious software, but this version exists almost only in DM; thus Axobot is not able to detect it, even less to prevent it.

Here are some examples of particularly blatant scams for context:

    | +100 FEEDBACK
    | +500 ORDERS
    |
    | NETFLIX ACCOUNTS
    | RANDOM STEAM KEYS X10 OR MORE!
    | AMAZON GIFT CARDS
    | [...]
    | ALL PAYMENT METHODS SUPPORTED, ALSO ACCEPTING XBOX AND NINTENDO DIGITAL CODES
    |
    | CHECK US OUT: **[CENSORED LINK]**
    |
    | TO PAY WITH PAYPAL OR SKRILL DM ME!
    | **[CENSORED LINK]**

--------

    | you got a credit or debit card? 🤣 if so link that on paypal and earn your winning.. i usually make about $20-$50 within 2 days or so

--------

    | looking to sell my account It has over 240 skins with black knight 1,000 v bucks + Mako glider and a lot of more Shii lemme know if you if want it
    |
    | Serious Buyers Only‼️


The advantage of this kind of message is that certain words or message characteristics come up often, like the high presence of capital letters or the words “free” and “nitro”. Of course a real detection will be more complex than that, but this is a first idea to create our model.

To put it simply, the scam detector is created in two phases: the learning phase, when the program reads and analyzes thousands of messages already knowing if they are scams or not, and then the testing phase, when it takes new messages and tries to predict if they are actually scams. The learning phase is crucial, because it needs to have a large enough and varied enough set of messages for the AI to be able to deduce similarities and rules, which will allow it to correctly detect scams, even when faced with messages written in a way he has never seen before.

.. note:: My tests with Axobot contain "only" about 2000 messages already classified, half of which are scam messages. As the bot will be used in real time, it will be able to collect more messages and thus improve its learning.


--------------------
The Technical Things
--------------------

Keep in mind that the system I describe here is the one in place at the time of writing (March 5, 2022), but it is likely to change along with my discoveries and optimizations.


Dataset Creation
----------------

It all starts with the creation of the dataset, which will be used by our agent (the AI) to train. To achieve this, Axobot scans many real messages from Discord and external datasets, and tries to detect their dangerousness.

But since the model is still in its beginnings, it needs to check if its classification is correct, it cannot base its learning only on what it already knows! Therefore, as soon as the bot thinks that a message is potentially a scam, it sends a confirmation request in a private channel before actually recording it as a scam. This system also allows us to verify that no personal data or sensitive messages are recorded in our database.

Once the raw message is recorded, our agent needs to analyze and clean it in order to get the maximum information from it. The very first process for this is called lemmatization: it consists in keeping only the root of each word, removing superfluous words (the “stop words”) and converting all capital letters into lower case. This makes it possible to ignore words that are too common, to make no difference between a word written in uppercase and the same word written in lower case, but also to detect scam messages using unusual Unicode characters instead of normal letters (ASCII)!

.. note:: For example, consider the following scam:

        \**LF EARLY SUPPORTER DM ASAP GOT CRAZY OFFERS** <a:Early:909664561093828659>  \|\| @everyone||

    Our lemmatization algorithm will convert it to this raw message:

        lf early support dm asap got crazy offer discordemoji everyon

This system is far from perfect, it will inevitably remove some important information, but it is still an essential step in the cleaning process.

To make it even better, other information is extracted from this message and will be used in the agent’s training: the percentage of capital letters, the number of Discord mentions, the number of punctuation marks, but also a “URL score” which indicates how suspicious the URLs in the message seem (for example a discord.gg link will look normal, bit.ly will be slightly suspicious and free-nitro.gg will be very suspicious). This last system has its own static algorithm separate from the AI.



The Actual Algorithm
--------------------

The learning algorithm itself is a Python implementation of Bayes’ algorithm. Concretely, it starts from a list of observations (the messages), each of which has attributes (the presence of a word, the number of punctuation marks or capital letters, etc.) and a single class (ham or scam). The agent will then use these attributes to build a “decision tree” which will allow, from an observation, to find the corresponding class. If you want to know more about this subject, there are many resources on the Internet.

To get more diversity in the answers, and in order to enhance learning, our agent creates many different versions of this Bayes decision tree, all using a certain percentage of the complete dataset. For example, we may want to create 300 trees, each using 70% of the dataset. We call this a random forest (again, there are many resources on this subject). The prediction of a random forest is usually the majority prediction of the trees in it (for example if out of 300 trees 273 predict “scam” and 27 “ham”, then the message will be treated as a “scam” with 91% certainty).


The Agent Evaluation
--------------------

It remains now to evaluate the performance of our agent. For this, the method is universal and very simple: the agent is trained on a large portion of the dataset (generally 80% of the observations), then we compare its predictions of the remaining observations with the already-known result. This allows us to test it on observations that it has never seen during its training phase, as if it were in real conditions. Obviously, the larger the dataset, the more correctly the agent will react to an unknown observation, because it will be able to generalize the characteristics of a typical scam message.

.. note:: On our current model, containing a thousand “scam” messages and about 800 safe messages, we obtain an accuracy score of about 85%—i.e., the agent responded correctly to 85% of the observations used for testing.



----------
Final note
----------

This is how the current scam detection system was built. It will most certainly evolve in the future, to adapt to new scam methods and constantly improve, but I hope to have at least made this system a bit less opaque for our users, without being too technical. If you have any questions about this, feel free to contact us on our support server (link in the homepage of this documentation or via the command ’about’).

I would like to thank my AI teacher from `CY Tech <https://cytech.cyu.fr/>`_ for listening to me for a long time and enlightening me on the best tracks to follow, this wonderful `tutorial on SMS spam detection <https://learn.vonage.com/blog/2020/11/19/sms-spam-detection-with-machine-learning-in-python/#>`__ which served as a basis for testing, Awhikax (co-admin of the bot) for the URLs scoring system, and all the documentation, blogs, tutorials and videos on the Internet which could help me and will help me to create this so complex system by myself. And, of course, all the users who will share their opinions and help me in one way or another!


*Stay safe!*
