# SENTINEL AI X - Deployment Guide

This guide provides step-by-step instructions for deploying the SENTINEL AI X platform. 
To operate on free-tier cloud providers, the architecture is split into two parts:
1. **Frontend:** Deployed on **Vercel** (Free, Serverless).
2. **Backend:** Deployed on **Render** (Free Web Service tier, using SQLite).

---

## 1. Prerequisites: GitHub OAuth App
Before deploying, you must create a GitHub OAuth application for user authentication.
1. Go to your GitHub Settings -> Developer Settings -> OAuth Apps -> **New OAuth App**.
2. **Application name:** `Sentinel AI X` (or similar)
3. **Homepage URL:** Your Vercel frontend URL (e.g., `https://obsidian-rwnd.vercel.app`)
4. **Authorization callback URL:** Your Vercel frontend URL + `/api/auth/callback/github` (e.g., `https://obsidian-rwnd.vercel.app/api/auth/callback/github`)
5. Generate a new **Client Secret**.
6. Save the **Client ID** and **Client Secret**. You will need them for the deployment steps below.

---

## 2. Deploying the Backend (Render)

We use Render's "Blueprint" feature to automatically configure the backend based on the `render.yaml` file included in this repository.

### Steps:
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click the **New +** button in the top right and select **Blueprint**.
3. Connect your GitHub repository (`MDWASIULLAH/obsidian`).
4. Render will automatically read the `render.yaml` file and prepare a Web Service called `sentinel-backend`.
5. You will be prompted to enter Environment Variables. Fill them out as follows:
   - `NVIDIA_API_KEY`: *(Leave blank or enter 'placeholder' if required)*
   - `GITHUB_TOKEN`: *(Leave blank or enter 'placeholder' if required)*
   - `GITHUB_ID`: Your GitHub OAuth App Client ID
   - `GITHUB_SECRET`: Your GitHub OAuth App Client Secret
   - `NEXTAUTH_URL`: Your Vercel frontend URL (e.g., `https://obsidian-rwnd.vercel.app`)
   - `FRONTEND_URL`: Your Vercel frontend URL (e.g., `https://obsidian-rwnd.vercel.app` - **No trailing slash!**)
6. Click **Apply** or **Save**.
7. Wait ~3-5 minutes for the deployment to finish. Once it shows a green **Live** badge, copy the URL displayed at the top left (e.g., `https://sentinel-backend-xxxx.onrender.com`). Keep this URL for the next step.

---

## 3. Deploying the Frontend (Vercel)

The frontend is a Next.js application located in the `/frontend` directory. 

### Steps:
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository (`MDWASIULLAH/obsidian`).
4. **CRITICAL STEP:** In the "Configure Project" screen, look for **Root Directory**. Click **Edit** and type `frontend`. This tells Vercel where the Next.js app is located.
5. Open the **Environment Variables** dropdown and add the following keys exactly as shown:
   - `NEXT_PUBLIC_API_URL`: The Render URL you copied in Step 2 (e.g., `https://sentinel-backend-xxxx.onrender.com`)
   - `NEXTAUTH_URL`: Your Vercel frontend URL (e.g., `https://obsidian-rwnd.vercel.app/`)
   - `NEXTAUTH_SECRET`: A random 32-character string (Generate one via `openssl rand -base64 32` or use the one previously generated).
   - `GITHUB_ID`: Your GitHub OAuth App Client ID
   - `GITHUB_SECRET`: Your GitHub OAuth App Client Secret
6. Click **Deploy**.
7. Wait 1-2 minutes for the build to finish. 

---

## 4. Final Verification
1. Open your Vercel URL in your browser.
2. Click **Login with GitHub**.
3. You should be redirected to GitHub to authorize the app.
4. After authorization, you will be redirected to the `/dashboard/setup` page.
5. The page will verify your session and prompt you to install the GitHub App to select repositories for analysis.

## Troubleshooting
- **GitHub Login gets stuck / 500 error:** Check the Render logs. Ensure the backend deployed successfully and is "Live". 
- **Vercel Build Error "No Next.js version detected":** You forgot to set the **Root Directory** to `frontend` in your Vercel project settings.
- **CORS Errors in browser console:** Ensure `FRONTEND_URL` in Render matches your exact Vercel URL (usually without the trailing slash `/`).
