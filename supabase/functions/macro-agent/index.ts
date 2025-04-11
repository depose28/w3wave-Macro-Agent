import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { OpenAI } from "https://esm.sh/openai@4.0.0"
import { Resend } from "https://esm.sh/resend@2.0.0"

// Initialize clients
const supabaseUrl = Deno.env.get('DB_URL')!
const supabaseKey = Deno.env.get('DB_SERVICE_KEY')!
const supabase = createClient(supabaseUrl, supabaseKey)

const openai = new OpenAI({
  apiKey: Deno.env.get('OPENAI_API_KEY'),
})

const resend = new Resend(Deno.env.get('SENDER_API_KEY'))

async function getTweetsFromSupabase(date: string) {
  try {
    const { data, error } = await supabase
      .from('messages')
      .select('*')
      .eq('date', date)

    if (error) throw error
    return data
  } catch (error) {
    console.error('Error getting tweets from Supabase:', error)
    return null
  }
}

async function generateAISummary(tweets: any[]) {
  const prompt = `You are a senior hedge fund analyst specializing in macro analysis. 
  Analyze the following tweets and provide a concise, insightful summary focusing on high-signal insights.
  Structure your analysis into clear sections with emoji headers:
  
  🧠 Macro
  🏛️ Politics & Geopolitics
  📊 Traditional Markets
  💰 Crypto Markets
  🔄 Observed Shifts in Sentiment or Tone
  
  For each insight, include the source tweet URL in parentheses.
  Focus on actionable insights and emerging trends.
  Keep the analysis professional and data-driven.`

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        { role: "system", content: prompt },
        { role: "user", content: JSON.stringify(tweets) }
      ],
      temperature: 0.7,
      max_tokens: 1000
    })

    return completion.choices[0].message.content
  } catch (error) {
    console.error('Error generating AI summary:', error)
    return null
  }
}

function formatEmailHTML(summaryText: string) {
  const timestamp = new Date().toISOString()
  return `
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
      <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px;">
          Daily Macro Update
        </h1>
        <div style="margin-top: 20px;">
          ${summaryText.replace(/\n/g, '<br>')}
        </div>
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px;">
          Generated at ${timestamp}
        </div>
      </div>
    </body>
    </html>
  `
}

async function sendEmailReport(summary: string) {
  try {
    const htmlContent = formatEmailHTML(summary)
    const timestamp = new Date().toISOString()
    const plainText = `Daily Macro Update\n\n${summary}\n\nGenerated at ${timestamp}`

    await resend.emails.send({
      from: Deno.env.get('EMAIL_SENDER')!,
      to: Deno.env.get('EMAIL_RECIPIENT')!,
      subject: "Daily Macro Update",
      html: htmlContent,
      text: plainText
    })

    return true
  } catch (error) {
    console.error('Error sending email:', error)
    return false
  }
}

async function main() {
  try {
    // Get today's tweets from database
    const today = new Date().toISOString().split('T')[0]
    const tweets = await getTweetsFromSupabase(today)

    if (!tweets || tweets.length === 0) {
      console.info("No tweets found for today")
      return { status: "success", message: "No tweets found for today" }
    }

    // Generate AI summary
    const summary = await generateAISummary(tweets)
    if (!summary) {
      console.error("Failed to generate AI summary")
      return { status: "error", message: "Failed to generate AI summary" }
    }

    // Send email report
    if (await sendEmailReport(summary)) {
      console.info("Email report sent successfully")
      return { status: "success", message: "Email report sent successfully" }
    } else {
      console.error("Failed to send email report")
      return { status: "error", message: "Failed to send email report" }
    }
  } catch (error) {
    console.error("Error in main function:", error)
    return { status: "error", message: String(error) }
  }
}

serve(async (req) => {
  try {
    const result = await main()
    return new Response(
      JSON.stringify(result),
      { 
        headers: { 
          'Content-Type': 'application/json',
          'Connection': 'keep-alive'
        }
      }
    )
  } catch (error) {
    console.error("Error in handler:", error)
    return new Response(
      JSON.stringify({ status: "error", message: String(error) }),
      { 
        status: 500,
        headers: { 
          'Content-Type': 'application/json',
          'Connection': 'keep-alive'
        }
      }
    )
  }
}) 