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
    bio: `Michael Boyce is a tech and policy expert who recently wrapped up his role as Director of the AI Corps at DHS, where he built the federal government's largest civilian AI team and hired 50 senior AI experts into the Department. Before that, he spent time at the White House helping write key AI policy, overseeing Western Hemisphere Foreign Assistance, and working at the United States Digital Service. He has over a decade of experience digitizing government processes and building machine learning systems across immigration and national security agencies. Earlier in his career, he worked directly as a Refugee Officer, leading teams in places like Ethiopia during a national emergency and reviewing complex refugee cases across Jordan, Kenya, Lebanon, Malaysia, and Turkey, before later using technology to lead the team that digitized the  U.S. refugee and asylum  application process. He lives in the Petworth neighborhood of Washington DC, and likes playing chess and finding good soup dumpling restaurants in the DC suburbs.`,
    github: "michaeleboyce",
    linkedin: "https://www.linkedin.com/in/michael-boyce-dhs-ai-corps/",
  },
  {
    name: "Abigail Haddad",
    role: "Creator and Machine Learning Engineer",
    bio: `Abigail Haddad is building modular tools for unstructured text data pipelines. She holds a PhD in Public Policy from RAND and has worked as a data scientist for the Department of the Army and, most recently, as a Machine Learning Engineer with DHS AI Corps. She blogs at presentofcoding.substack.com.`,
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
