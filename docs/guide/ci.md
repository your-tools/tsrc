# Using tsrc with Continuous Integration (CI)

## GitHub Actions

Let suppose you have a private GitHub organization holding several private
repositories and tsrc to synchronize them using the SSH protocol. Let suppose
you want to use [GitHub Actions](https://docs.github.com/en/actions) to download
the code source of your organization, compile it and run some non regression
tests. What to write to achieve this with tsrc?

### Step 1: Your tsrc manifest

Your tsrc `manifest.yml` looks something like this:

```
repos:
  - url: git@github.com:project1/foo
    dest: foo
```

The `git@` means SSH protocol.

### Step 2: Create your GitHub workflows file

In your private GitHub repository holding the GitHub workflows files, create the
folder `.github/workflows` and your yaml file with the desired name and the
following content. For more information about GitHub actions syntax see this
[video](https://youtu.be/R8_veQiYBjI):

```
name: tsrc with private github repos
on:
  workflow_dispatch:
    branches:
      - main

jobs:
  export_linux:
    runs-on: ubuntu-latest
    steps:
    - name: Installing tsrc tool
      run: |
        sudo apt-get update
        sudo apt-get install -y python3
        python -m pip install tsrc

    - name: Cloning private github repos
      run: |
        git config --global url."https://${{ secrets.ACCESS_TOKEN }}@github.com/".insteadOf git@github.com:
        export WORKSPACE=$GITHUB_WORKSPACE/your_project
        mkdir -p $WORKSPACE
        cd $WORKSPACE
        tsrc init git@github.com:yourorganisation/manifest.git
        tsrc sync
```

This script will run on the latest Ubuntu Docker and trigs two steps:
- The first step named `Installing tsrc tool` allows to install python3 and then
  tsrc.
- The second step named `Cloning private github repos` creates a folder named
  `your_project` for your workspace and call the initialisation and
  synchronization of your repositories.

The important command is:
```
git config --global url."https://${{ secrets.ACCESS_TOKEN }}@github.com/".insteadOf git@github.com:
```

which allows to replace the SSH syntax by the HTTPS syntax on your GitHub repository names.

### Step 3: Create the GitHub secret

For GitHub organization one member of the team has the responsibility to hold a
`Personal access tokens` for the organization. Go https://github.com/settings/tokens
and click on the button `Generate new token` then click on `repo` checkbox then click
on the button `Generate token`.

Now, this token shall be saved into an action secret named `ACCESS_TOKEN` inside
the GitHub repository holding the GitHub workflows files.

### Step 4: Enjoy

In the menu `Actions` of your repository you can trig the worflow. In this
example we used `workflow_dispatch` to perform manual triggers. So click on the
button to start the process. Once this step done with success, you can update
your workflow yaml to complete your CI work: compilation of your project, run
non regression tests, etc.
