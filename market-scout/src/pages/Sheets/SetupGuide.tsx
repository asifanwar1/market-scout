import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type TSetupGuideProps = {
    // Open for someone still connecting; folded away once it works.
    defaultOpen: boolean;
};

const STEPS = [
    <>
        Open <span className="font-medium">console.cloud.google.com</span> and sign in with a Google account. Create a project (any name) or pick an existing one. It is free and needs no
        billing card.
    </>,
    <>
        Go to <span className="font-medium">APIs &amp; Services → Library</span>, search for <span className="font-medium">Google Sheets API</span> and press <span className="font-medium">Enable</span>.
    </>,
    <>
        Go to <span className="font-medium">IAM &amp; Admin → Service Accounts → Create service account</span>. Name it "market-scout" and press Done (no roles are needed).
    </>,
    <>
        Open the new service account, choose <span className="font-medium">Keys → Add key → Create new key → JSON</span>. A small file downloads to your computer.
    </>,
    <>
        Open that file in Notepad, copy everything in it and paste it into <span className="font-medium">step 1</span> below.
    </>,
    <>
        Create a Google Sheet (or pick one), press <span className="font-medium">Share</span>, and add the email address shown in step 1 as an <span className="font-medium">Editor</span>. Then paste the
        sheet's link into <span className="font-medium">step 2</span>.
    </>,
];

const SetupGuide = ({ defaultOpen }: TSetupGuideProps) => {
    return (
        <Card>
            <CardHeader>
                <CardTitle>How to set this up</CardTitle>
                <CardDescription>A one-time job of about five minutes. Market Scout signs in to Google as a robot account (a "service account") of its own, so nobody's personal Google password is involved.</CardDescription>
            </CardHeader>
            <CardContent>
                <details open={defaultOpen} className="group">
                    <summary className="cursor-pointer text-sm font-medium text-primary group-open:mb-3">
                        <span className="group-open:hidden">Show the steps</span>
                        <span className="hidden group-open:inline">Hide the steps</span>
                    </summary>
                    <ol className="list-decimal space-y-2 pl-5 text-sm">
                        {STEPS.map((step, index) => (
                            <li key={index}>{step}</li>
                        ))}
                    </ol>
                </details>
            </CardContent>
        </Card>
    );
};

export default SetupGuide;
