import { test, expect } from "@playwright/test";
import path from "node:path";
test("multi-file CSV and workbook ingestion redirects to live dashboards",async({page,request})=>{
 const email=`workbook_${Date.now()}@example.com`;
 expect((await request.post("/api/v1/auth/register",{data:{email,password:"WorkbookPass123!",full_name:"Workbook Audit"}})).ok()).toBeTruthy();
 const login=await request.post("/api/v1/auth/login",{data:{email,password:"WorkbookPass123!"}});
 const token=(await login.json()).access_token as string;
 await page.addInitScript((value:string)=>localStorage.setItem("lumen_access_token",value),token);
 await page.goto("/datasets");
 await page.locator('input[type="file"]').setInputFiles(["sales.csv","customers.csv","products.xlsx"].map(name=>path.resolve(process.cwd(),"../sample_data",name)));
 await expect(page).toHaveURL(/dashboards/,{timeout:25000});
 await expect(page.getByText("Files analyzed")).toBeVisible({timeout:15000});
 const response=await request.get("/api/v1/datasets",{headers:{Authorization:`Bearer ${token}`}});
 const datasets=await response.json();expect(datasets).toHaveLength(4);
 expect(new Set(datasets.map((d:{table_name:string})=>d.table_name)).size).toBe(4);
 await expect(page.getByText("SQL",{exact:true}).first()).toBeVisible();
});
