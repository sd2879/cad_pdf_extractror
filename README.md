# The Soap Factory Project

This repo contains the code used to create a visual representation of the Work Breakdown Structure (WBS) for the Soap Factory work.

The application can be accessed at [https://the-soap-factory-project.replit.app/](https://the-soap-factory-project.replit.app/).

## Contributing

The code for this project is hosted on [Replit](https://replit.com/@virgelsnake/The-Soap-Factory-Project), which can be used as an IDE for developing the application. You will need to be granted access to use this instance on Replit.

It is also possible to work on this repository locally and push changes via Pull Request.

> **PLEASE DO NOT COMMIT CODE DIRECTLY TO THE MAIN BRANCH**

## Working on Replit

### Development process

1. Ask for access.
2. To make changes to the code, first create a new branch.
  1. Open the **Git** tab.
  2. At the top of the tab there is a drop down containing the names of the current branches. Ensure that you are on the branch that you want to use as a base for your new branch. If in doubt, choose `main`.
  3. To create a new branch, open that same drop down and type the name you want to give your branch in the search box starting with your initials so it's easy to see who's working on what, i.e. `acg-adding-feature-x`.
  4. Assuming there is not already a branch with that name, you will be prompted to create the new branch. Doing so will create the branch and then switch you to it.
3. Work on the code directly in Replit.
4. Regularly use the **Git** tab as you work to commit your changes. It is also good practice to use the **Push branch...** button to push your changes up to GitHub. After you do this for the first time with a new branch, this button will change to a **Sync with Remote** button.
5. When you are ready to submit your work, use the **Git** tab to ensure all your code is committed and pushed to GitHub. Use the ellipsis (...) button to access the menu for your branch and select **New Pull Request** to create a PR for your changes.
6. One of the repo admins will then review your Pull Request. Once approval is granted, your PR will be merged to the `main` branch for you. The admin will then ensure that Replit is updated to remove your branch and update the version of the `main` branch there. They will also deploy your code.

### Running

In Replit, hitting the **Run** button should be all you need to get up and running. The Webview will then show the application.

## Working on your own machine

To pull the code locally, [clone the repo](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories).

### Prerequisites

You'll need to have [NodeJS](https://nodejs.org/en) installed on your local machine. At time of writing, the version of NodeJS was 20.x.

The code also uses a SQLite3 database for local development. You'll need to [install it](https://www.sqlite.org/download.html) locally if you're not working on Replit.

### Development process

1. Create a branch to work on using the naming convention `<your initials>-<name-of-the-branch>`, i.e. `acg-adding-feature-x`.
2. When you're ready to submit your changes, create a PR on GitHub.
3. One of the repo admins will then review your Pull Request. Once approval is granted, your PR will be merged to the `main` branch for you.
4. The admin will also ensure that Replit is updated accordingly. They will also deploy any changes.

### Running

From the root of the project:

```shell
# install dependencies
npm install

# start the local server
npm run start
```

Now visit [http://localhost:3000](http://localhost:3000) to run the application in your browser.

## Deploying

The application is deployed using [Replit](https://replit.com/@virgelsnake/The-Soap-Factory-Project). On the **Deployments** tab, click the **Redeploy** button to deploy the latest changes on the `main` branch.

The application can be accessed at [https://the-soap-factory-project.replit.app/](https://the-soap-factory-project.replit.app/).

## Data

In Replit, and when deployed, we use Replit's built-in Key-Value Database. On our local machines we don't have access to Replit's DB, so we're using SQLite instead. The application decides which DB to use based on an environment variable `USE_REPLIT_DB`. This is set in Replit using Secrets for development and Deploy Secrets for deployed applications.

When set to `true`, the application will use the Replit DB. When set to `false`, the application will use a local SQLite database in a file called `tree.db` in the `db` folder. If the environment variable is not explicitly set, it will default to `false` and SQLite will be used.

### Seeding and emptying the database

There are two commands that help us to refresh a database: `npm run db:seed` and `npm run db:empty`.

#### Seeding

Running `npm run db:seed` first checks to see if the database is empty. If it is not, the process will end with a message saying the database is not empty and no data will be added. If the database is empty, the `data.json` file in the project root folder will be used to populate the database with an initial WBS.

#### Emptying

**CAUTION: YOU WILL NOT BE PROMPTED FOR CONFIRMATION WHEN RUNNING THIS ACTION AND IT IS NOT REVERSIBLE. DO NOT USE UNLESS YOU HAVE A BACKUP AND KNOW WHAT YOU'RE DOING!!**

Running `npm run db:empty` will delete all node data from the database.
