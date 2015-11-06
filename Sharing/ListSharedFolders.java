/*
 * BUILD INSTRUCTIONS:
 * Rename the accompanying ListSharedFolders-pom.xml file to pom.xml and run the following, 
 * where -f indicates the output filename and an optional -e flag searches external folders only:
 * 		clean compile assembly:single
 * 		java -jar target/ListSharedFolders-0.0.1-jar-with-dependencies.jar -f=<OUTPUT_FILENAME>
 * 
 */

import java.io.FileWriter;
import java.io.IOException;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Scanner;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.apache.commons.cli.*;
import org.apache.http.Header;
import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.config.CookieSpecs;
import org.apache.http.client.methods.*;
import org.apache.http.config.Registry;
import org.apache.http.config.RegistryBuilder;
import org.apache.http.conn.util.PublicSuffixMatcherLoader;
import org.apache.http.cookie.CookieSpecProvider;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.cookie.DefaultCookieSpecProvider;
import org.apache.http.message.BasicHeader;
import org.apache.http.util.EntityUtils;
import org.json.*;


import com.opencsv.CSVWriter;

/**
 *  App to search an external folders and output the results
 */
public class ListSharedFolders {

  private String token;
  private CSVWriter writer;
  private String logFile;
  private Set<String> visitedFolders = new HashSet<String>();
  private boolean externalOnly;
  
  public ListSharedFolders(String[] args, String token) throws IOException {
    CommandLine parsedArgs = parseArgs(args);
    logFile = parsedArgs.getOptionValue('f');
    externalOnly = parsedArgs.hasOption('e');
    this.token = token;
  }

  /**
   * Main - run the app
   * 
   * @param args CLI input
   * @throws ExecutionException 
   * @throws InterruptedException 
   */
  public static void main(String[] args) throws IOException, InterruptedException, ExecutionException {
	  
	  Scanner reader = new Scanner(System.in);
	  System.out.println("Enter your Dropbox Business API App token (Team Member File Access permission): ");
	  String token = reader.nextLine(); 
	  
	  ListSharedFolders sr = new ListSharedFolders(args, token);
	  sr.search();
  }

  /**
   * Run the search
   * 
   * @param args CLI arguments
   * @throws ExecutionException 
   * @throws InterruptedException 
   */
  public void search() throws IOException, InterruptedException, ExecutionException {
    int sharedFolderCount = 0;

    // Write log file header
    writer = new CSVWriter(new FileWriter(logFile), ',');
    writer.writeNext(new String[] { 
        "Shared Folder Name", 
        "Link Policy", 
        "Owner", 
        "Owner on Team", 
        "Team Members", 
        "External Members"
    });

    ExecutorService threadPool = Executors.newFixedThreadPool(10);
    List<Future<Integer>> counts = new ArrayList<Future<Integer>>();
    
    // Fetch each page of users
    String cursor = null;
    boolean hasMore = true;
    int pageSize = 20;

    while (hasMore) {

      JSONObject memberResponse = new JSONObject(postJson("team/members/list", token, "{\"limit\":" + pageSize + (cursor == null ? "" : ",\"cursor\":\"" + cursor + "\"") + "}", null));
      hasMore = memberResponse.getBoolean("has_more");
      cursor = memberResponse.getString("cursor");
      JSONArray members = memberResponse.getJSONArray("members");

      // Handle each member
      for (int i = 0; i < members.length(); i++) {
        counts.add(threadPool.submit(new UserFolderCall(members.getJSONObject(i))));
      }
    }

    threadPool.shutdown();
    for (Future<Integer> i:counts) {
      sharedFolderCount += i.get();
    }
    
    writer.close();

    System.out.println("Done. Found " + sharedFolderCount + " shared folders");
  }

  /**
   * Search as a user and handle the hits
   * 
   * @param member
   * @return
   * @throws IOException
   */
  private class UserFolderCall implements Callable<Integer> {
    private JSONObject member;
    
    private UserFolderCall(JSONObject member) {
      this.member = member;
    }
    
    public Integer call() throws IOException {
    	
      int searchHits = 0;
  
      JSONObject profile = member.getJSONObject("profile");
  
      String memberId = profile.getString("member_id");
      String name = profile.get("given_name") + " " + profile.get("surname");
      String email = profile.getString("email");
  
      System.out.println("Searching user " + name + " (" + email + ")");
      
      if (!profile.getString("status").equals("active")) {
        return 0; // we can't search inactive users
      }
      
      JSONArray sharedFolders = new JSONArray(getJson("shared_folders?include_membership=true", token, memberId));
      for (int i=0; i< sharedFolders.length(); i++) {
        JSONObject folder = sharedFolders.getJSONObject(i);
        
        // check if we've seen the folder before
        String id = folder.getString("shared_folder_id");
        if (visitedFolders.contains(id)) {
          continue;
        } else {
          visitedFolders.add(id);
        }
  
        // get team members
        StringBuffer teamShares = new StringBuffer();
        StringBuffer externalShares = new StringBuffer();
        
        JSONArray sharedMembers = folder.getJSONArray("membership");
        
        for (int m = 0; m < sharedMembers.length(); m++) {
          JSONObject sharedMember = sharedMembers.getJSONObject(m).getJSONObject("user");
          
          // same team
          if (sharedMember.has("same_team") && sharedMember.getBoolean("same_team")) {
            teamShares.append(teamShares.length() == 0 ? "" : ", ");
            teamShares.append(sharedMember.getString("display_name") + (sharedMember.has("email") ? " ("+sharedMember.getString("email")+")" : "") );
          
          // not same team - must be external share
          } else {
            externalShares.append(externalShares.length() == 0 ? "" : ", ");
            externalShares.append(sharedMember.getString("display_name") + (sharedMember.has("email") ? " ("+sharedMember.getString("email")+")" : "") );
          }
        }
        
        JSONObject owner = (folder.has("owner") && !JSONObject.NULL.equals(folder.get("owner")) ? folder.getJSONObject("owner") : null);
        boolean ownerOnTeam = (owner != null &&  (owner.has("same_team") && owner.getBoolean("same_team") ) );
        
        if (!externalOnly || !ownerOnTeam || externalShares.length() > 0 ) {
          searchHits++;

          synchronized (writer) {
            writer.writeNext(new String[]{
                folder.getString("shared_folder_name"), 
                folder.getString("shared_link_policy"), 
                owner == null ? "(deleted)" : owner.getString("display_name") + (owner.has("email") ? " ("+owner.getString("email")+")" : "") , 
                ownerOnTeam ? "yes" : "no", 
                teamShares.toString(), 
                externalShares.toString()
            });
          }
        }
      }
      
      return searchHits;
    }
  }


  /**
   * Gets JSON (as a member, if specified), gets a String response
   * 
   * @param call
   * @param token
   * @param body JSON body
   * @return
   * @throws IOException
   */
  private static String getJson(String call, String token, String memberId) throws IOException {
    return httpCall(new HttpGet("https://api.dropbox.com/1/" + call), token, memberId);
  }

  /**
   * Posts JSON (as a member, if specified), gets a String response
   * 
   * @param call
   * @param token
   * @param post
   * @param memberId
   * @return
   * @throws IOException
   */
  private static String postJson(String call, String token, String post, String memberId) throws IOException {
    HttpPost request = new HttpPost("https://api.dropbox.com/1/" + call);
    request.setEntity(new ByteArrayEntity(post.getBytes()));
    return httpCall(request, token, memberId);
  }
  
  /**
   * Posts JSON as a member, gets a String response
   * 
   * @param call
   * @param token
   * @param body JSON body
   * @return
   * @throws IOException
   */
  private static String httpCall(HttpRequestBase request, String token, String memberId) throws IOException {
    List<Header> headers = new ArrayList<Header>();
    headers.add(new BasicHeader("Content-Type", "application/json"));
    headers.add(new BasicHeader("Authorization", "Bearer "+URLEncoder.encode(token, "UTF-8")));
    if (memberId != null) {
      headers.add(new BasicHeader("X-Dropbox-Perform-As-Team-Member", memberId));
    }
    
    // Use custom CookieSpecProvider to handle Dropox date formats in headers
    Registry<CookieSpecProvider> r = RegistryBuilder.<CookieSpecProvider>create().register(CookieSpecs.DEFAULT, 
    		new DefaultCookieSpecProvider(DefaultCookieSpecProvider.CompatibilityLevel.DEFAULT,   
    				PublicSuffixMatcherLoader.getDefault(), new String[]{"E, dd MMM yyyy HH:mm:ss zzz"}, false)).build();
    HttpClient client = HttpClients.custom().setDefaultHeaders(headers).setDefaultCookieSpecRegistry(r).build();

    HttpResponse response = client.execute(request);
    String body = EntityUtils.toString(response.getEntity());

    // Check for 500
    if (response.getStatusLine().getStatusCode() >= 500) {
      throw new IOException("Dropbox "+response.getStatusLine().getStatusCode()+" error");

    // Check for 400x - we should get an error in the JSON Object response
    } else if (response.getStatusLine().getStatusCode() >= 400) {
      JSONObject ret = new JSONObject(body);
      if (ret.has("error")) { 
        throw new IOException("Dropbox API Error: "+ret.get("error")+" (HTTP "+response.getStatusLine().getStatusCode()+")");
      } else if (ret.has("error_description")) {
        throw new IOException("Dropbox API Error: "+ret.get("error_description")+" (HTTP "+response.getStatusLine().getStatusCode()+")");
      }
    }

    return body;
  }

  /**
   * Returns the CLI options object
   * 
   * @return
   */
  private static Options options() {
    Options options = new Options();
    options.addOption(Option.builder("f").longOpt("file").hasArg(true).desc("CSV Log to Write").required(true).build());
    options.addOption(Option.builder("h").longOpt("help").hasArg(false).desc("Display Help").build());
    options.addOption(Option.builder("e").longOpt("external").hasArg(false).desc("External Folders Only").build());
    return options;
  }

  /**
   * Prints CLI usage help
   */
  private static void usage() {
    HelpFormatter formatter = new HelpFormatter();
    formatter.printHelp(ListSharedFolders.class.getSimpleName() + ": exports a list of shared folders on the team.", options());
    System.exit(0);
  }

  /**
   * Parse CLI argument string into an object
   * 
   * @param args
   * @return
   */
  private static CommandLine parseArgs(String[] args) {
    CommandLineParser parser = new DefaultParser();
    try {
      CommandLine cl = parser.parse(options(), args);
      if (cl.hasOption('h')) {
        usage();
      }
      return cl;
    } catch (ParseException e) {
      System.out.println("Error: " + e.getMessage());
      usage();
      return null;
    }
  }
}