// src/app/attribution/page.tsx
import { Metadata } from "next";
import AttributionCard from "@/components/AttributionCard";

/**
 * Page metadata – this is picked up by the Next.js App Router.
 */
export const metadata: Metadata = {
  title: "Attribution – Schedule F Analysis",
  description:
    "Meet the people behind the Schedule F Analysis project and learn how to connect with them.",
};

/**
 * Simple helper to build an avatar URL from a GitHub username.
 */
const githubAvatar = (username: string, size = 240) =>
  `https://github.com/${username}.png?size=${size}`;

/**
 * Data‑driven description of contributors so the component markup stays tidy.
 */
const CONTRIBUTORS = [
  {
    name: "Michael Boyce",
    role: "Application Developer and Recovering ex-Federal Employee",
    bio: `Former Chief of Innovation for the Refugee and Asylum Programs at USCIS, Michael led the roll‑out of the agency's first refugee case‑management system and now works on AI in the public interest. He is the instigator of this Schedule F public‑comment explorer and loves long walks, chess, and TypeScript.`,
    github: "michaeleboyce",
    linkedin: "https://www.linkedin.com/in/michael-boyce-dhs-ai-corps/",
  },
  {
    name: "Abigail Haddad",
    role: "Creator and Machine Learning Engineer",
    bio: `Abigail is a data scientist with deep expertise in federal procurement and civic‑tech policy. She develops clustering and PCA visualisations that help make sense of thousands of public comments, ensuring transparency and rigour in the analysis.`,
    github: "abigailhaddad",
    linkedin: "https://www.linkedin.com/in/abigail-haddad/",
  },
];

export default function AttributionPage() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col">
      <div className="container mx-auto px-4 md:px-8 py-10">
        <h1 className="text-3xl md:text-4xl font-extrabold text-gray-800 mb-8 flex items-center gap-2">
          <span aria-hidden="true">👥</span>
          Project Attribution
        </h1>

        <div className="grid gap-8 md:grid-cols-2">
          {CONTRIBUTORS.map(({ name, role, bio, github, linkedin }) => (
            <AttributionCard
              key={name}
              name={name}
              role={role}
              bio={bio}
              github={github}
              linkedin={linkedin}
              avatarUrl={githubAvatar(github)}
            />
          ))}
        </div>
      </div>
    </main>
  );
}
