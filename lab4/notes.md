**1.** `--global` saves the setting in `~/.gitconfig` in my home folder, so it applies to every Git repository on my laptop. If I leave it out, the setting is saved only in `.git/config` of the repo I'm currently in, and it overrides the global setting just for that repo. That's how my name and email (`mstspg1204 <singhal.maira@gmail.com>`) got attached to every commit I made.

**2.** Running `ls -a` showed me the hidden `.git` folder, which normal `ls` doesn't show because it starts with a dot. Inside it I found `HEAD`, `config`, `description`, `hooks/`, `info/`, `objects/` and `refs/`, and after committing also `index`, `logs/` and `COMMIT_EDITMSG`. I understood that `.git` is the actual repository — it stores all my commits and history, and if I deleted it the folder would just become normal files again.

**3.** `git status` showed me four untracked entries: `.DS_Store`, `lab4/`, `week01/` and `week02/`. The actual number of files is more than that, because Git shows a whole untracked folder as one line, so all the files inside `week01/` and `week02/` count too. The untracked code is in those week folders, while `.DS_Store` is just a macOS system file and not code.

**4.** After I created `.gitignore` and added `.DS_Store` to it, `.DS_Store` stopped appearing in `git status`. But `.gitignore` itself showed up as a new untracked file, because Git treats it like any other new file until I add it.

**5.** `.gitignore` should be committed because the ignore rules are part of the project, not just my laptop. If I commit it, anyone who clones the repo gets the same rules and won't accidentally commit junk like `.DS_Store`. If I ignored it, the rules would only work on my machine.

**6.** Git has three places: the working directory, the staging area and the repository. When I edited `README.md`, it showed up as modified in the working directory. After `git add README.md` it moved to "Changes to be committed", which is the staging area. After `git commit` it disappeared from `git status` completely, because it was saved in the repository and there was nothing left to commit.

**7.** When I committed my README, Git printed `[master 167a8bf] Write README` and `1 file changed, 13 insertions(+)`. This shows the branch I'm on, the short hash of the commit, my commit message, and a summary of the changes. Only one file was changed, which was `README.md`.

**8.** The first seven characters are called the short hash. The full commit hash is 40 characters long — my first commit's full hash was `51e3208e7fa4102f41f942f4fdb3414bb2155850` — and it's a unique ID made from the commit's contents. Seven characters are enough to identify a commit uniquely in a small project, so `git log --oneline` shows it as `51e3208` and I can use that in Git commands instead of typing the full hash.

**9.** The four steps are: edit my files, `git add` to stage the changes, `git commit` to save a snapshot locally, and `git push` to upload it to GitHub. I also kept running `git status` in between to check where my files were.

**10.** `README.md` goes in the root folder of the repository and explains what the project is and what's inside it. Git itself doesn't treat it differently, but GitHub uses it as the description of the project.

**11.** `gh auth login` logged me in through my browser using a one-time code and saved an access token on my laptop. When it asked "Authenticate Git with your GitHub credentials?" I chose yes, which set up Git to use that token automatically. So now when I push, Git uses the saved token instead of asking me for a password.

**12.** GitHub shows `README.md` on the front page of the repository. It automatically looks for a README in the root folder and displays it as formatted text below the file list, so it's the first thing someone sees when they open my repo.

**13.** `git push` does not change my local history at all — it only copies my commits to GitHub. When I ran `git log --oneline` after pushing, I had the same four commits with the same hashes in the same order. The only difference was that `origin/master` now appeared next to my latest commit `72a15f7`, which shows that GitHub's copy matches mine.

**14.** A private repository actually exists on GitHub with all its commits, but only I and people I invite can see it. If I don't create a repository at all, there's nothing there. To someone else both look the same, because GitHub shows a 404 page for private repos so it doesn't reveal that they exist. The difference matters for me: I can push to my private repo, but pushing to a repo that doesn't exist fails with "Repository not found".

